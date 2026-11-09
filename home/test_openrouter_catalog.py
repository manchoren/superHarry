import json
from io import BytesIO, StringIO
from types import SimpleNamespace
from unittest.mock import Mock, patch
import subprocess

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase

from home.openrouter_catalog import CatalogCache, CatalogError, CatalogModel, _FETCH_PROGRAM, fetch_catalog, parse_catalog


def model(model_id="example/model:free", **overrides):
    value = {
        "id": model_id,
        "context_length": 4096,
        "architecture": {"input_modalities": ["text"], "output_modalities": ["text"]},
        "pricing": {"prompt": "0", "completion": "0", "request": "0", "image": "0"},
    }
    value.update(overrides)
    return value


class OpenRouterCatalogTests(SimpleTestCase):
    def parse(self, entries):
        return parse_catalog(json.dumps({"data": entries}).encode())

    def test_only_free_text_models_with_all_zero_listed_prices_are_returned(self):
        entries = [model(), model("example/paid:free", pricing={"prompt": "0", "completion": "0.01", "request": "0"}),
                   model("example/uncertain:free", pricing={"prompt": "0"}),
                   model("example/paid"), model("openai/model:free"), model("example/image:free", architecture={"input_modalities": ["image"], "output_modalities": ["text"]}),
                   model("example/boolean:free", context_length=True)]
        self.assertEqual(self.parse(entries), (CatalogModel("example/model:free", 4096),))

    def test_duplicate_model_ids_are_excluded(self):
        self.assertEqual(self.parse([model(), model()]), ())
        self.assertEqual(self.parse([model(context_length=False), model()]), ())

    def test_unknown_and_nonfinite_prices_are_excluded(self):
        for price in ("NaN", "Infinity", "0.01", 0, ""):
            with self.subTest(price=price):
                self.assertEqual(self.parse([model(pricing={"prompt": "0", "completion": "0", "request": "0", "other": price})]), ())

    def test_malformed_and_duplicate_json_are_rejected(self):
        for raw in (b'{"data":[],"data":[]}', b'{"data":NaN}', b'\xff'):
            with self.subTest(raw=raw), self.assertRaises(CatalogError):
                parse_catalog(raw)

    def test_response_and_entry_count_limits(self):
        with self.assertRaises(CatalogError):
            parse_catalog(b" " * (4 * 1024 * 1024 + 1))
        with self.assertRaises(CatalogError):
            self.parse([None] * 10001)
        self.assertEqual(self.parse([None] * 10000), ())

    @patch("home.management.commands.inspect_openrouter_catalog.fetch_catalog")
    def test_command_reports_metadata_warning_without_enabling_routes(self, fetch):
        fetch.return_value = (CatalogModel("example/model:free", 4096),)
        out = StringIO()
        call_command("inspect_openrouter_catalog", stdout=out)
        self.assertIn("does not verify total cost", out.getvalue())
        self.assertIn("example/model:free\t4096", out.getvalue())

    @patch("http.client.HTTPSConnection")
    def test_fetch_uses_fixed_origin_and_refuses_redirects(self, connection_factory):
        connection = connection_factory.return_value
        response = connection.getresponse.return_value
        response.status = 302
        with self.assertRaises(SystemExit):
            exec(_FETCH_PROGRAM, {})
        connection_factory.assert_called_once_with("openrouter.ai", timeout=5)
        connection.request.assert_called_once_with("GET", "/api/v1/models", headers={"Accept": "application/json"})
        connection.close.assert_called_once()

    @patch("http.client.HTTPSConnection")
    def test_fetch_parses_success_and_closes_connection(self, connection_factory):
        connection = connection_factory.return_value
        response = connection.getresponse.return_value
        response.status = 200
        response.read.return_value = json.dumps({"data": [model()]}).encode()
        output = SimpleNamespace(buffer=BytesIO())
        with patch('sys.stdout', output):
            exec(_FETCH_PROGRAM, {})
        self.assertEqual(parse_catalog(output.buffer.getvalue()), (CatalogModel("example/model:free", 4096),))
        response.read.assert_called_once_with(4 * 1024 * 1024 + 1)
        connection.close.assert_called_once()

    @patch("home.openrouter_catalog.subprocess.run")
    def test_fetch_fails_closed_on_http_error_and_absolute_timeout(self, run):
        run.return_value = SimpleNamespace(returncode=1, stdout=b'')
        with self.assertRaises(CatalogError):
            fetch_catalog()
        self.assertEqual(run.call_args.kwargs['timeout'], 10)
        self.assertNotIn('OPENROUTER_API_KEY', run.call_args.kwargs['env'])
        run.side_effect = subprocess.TimeoutExpired('synthetic', 10)
        with self.assertRaisesRegex(CatalogError, "^catalog_unavailable$"):
            fetch_catalog()

    @patch("home.management.commands.inspect_openrouter_catalog.fetch_catalog")
    def test_command_reports_bounded_error(self, fetch):
        fetch.side_effect = CatalogError("private details")
        with self.assertRaisesRegex(CommandError, "^OpenRouter catalog is unavailable or invalid\\.$"):
            call_command("inspect_openrouter_catalog", stdout=StringIO())

    @patch('home.openrouter_catalog.threading.Thread')
    @patch('home.openrouter_catalog.time.monotonic')
    @patch('home.openrouter_catalog.fetch_catalog')
    def test_cache_is_nonblocking_single_flight_and_never_serves_expired_data(self, fetch, clock, thread):
        clock.return_value = 100
        fetch.return_value = (CatalogModel('example/model:free', 4096),)
        cache = CatalogCache(ttl=5)
        self.assertEqual(cache.get(), ())
        self.assertEqual(cache.get(), ())
        thread.assert_called_once()
        fetch.assert_not_called()
        cache._refresh()
        self.assertEqual(cache.get(), fetch.return_value)
        clock.return_value = 105
        self.assertEqual(cache.get(), ())
        self.assertEqual(thread.call_count, 2)

    @patch('home.openrouter_catalog.threading.Thread')
    @patch('home.openrouter_catalog.time.monotonic', return_value=100)
    @patch('home.openrouter_catalog.fetch_catalog', side_effect=OSError('private details'))
    def test_cache_failure_is_empty_and_does_not_expose_error(self, fetch, clock, thread):
        cache = CatalogCache(ttl=5)
        self.assertEqual(cache.get(), ())
        cache._refresh()
        self.assertEqual(cache.get(), ())
        self.assertEqual(thread.call_count, 1)

    @patch('home.openrouter_catalog.threading.Thread')
    @patch('home.openrouter_catalog.time.monotonic', return_value=100)
    @patch('home.openrouter_catalog.fetch_catalog')
    def test_worker_can_wait_for_cold_cache_but_timeout_is_fail_closed(self, fetch, clock, thread):
        cache = CatalogCache(ttl=5)
        cache._ready = Mock()
        self.assertEqual(cache.get(wait=True), ())
        cache._ready.wait.assert_called_once_with(12)
        fetch.return_value = (CatalogModel('example/model:free', 4096),)
        cache._refresh()
        self.assertEqual(cache.get(wait=True), fetch.return_value)

    @patch('home.openrouter_catalog.fetch_catalog')
    def test_independent_cold_web_and_api_caches_wait_for_their_own_snapshots(self, fetch):
        fetch.return_value = (CatalogModel('example/model:free', 4096),)
        web, api = CatalogCache(), CatalogCache()
        self.assertEqual(web.get(wait=True), fetch.return_value)
        self.assertEqual(api.get(wait=True), fetch.return_value)
        self.assertEqual(fetch.call_count, 2)


class OpenRouterApprovalTests(SimpleTestCase):
    @patch("home.openrouter_transport.cached_catalog")
    def test_only_owner_approved_available_models_are_routable(self, catalog):
        from home.openrouter_transport import catalog_models
        approved = CatalogModel("liquid/lfm-2.5-2.6b:free", 65536)
        new_model = CatalogModel("example/new:free", 4096)
        catalog.return_value = (approved, new_model)
        self.assertEqual(catalog_models(wait=True), (approved,))

    @patch("home.management.commands.inspect_openrouter_catalog.fetch_catalog")
    def test_pull_distinguishes_new_and_missing_models(self, fetch):
        fetch.return_value = (CatalogModel("example/new:free", 4096),)
        out = StringIO()
        call_command("inspect_openrouter_catalog", stdout=out)
        self.assertIn("example/new:free\t4096\tpending approval", out.getvalue())
        self.assertIn("liquid/lfm-2.5-2.6b:free\tunavailable", out.getvalue())
