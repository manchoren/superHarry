from unittest import TestCase

from home.web_fetch_staging import (
    FetchPolicyError,
    validate_destination,
    validate_redirect_chain,
)


class T194WebFetchPolicyTests(TestCase):
    def resolver(self, hostname, _port):
        return {
            "public.example": ["93.184.216.34"],
            "private.example": ["10.0.0.8"],
            "mixed.example": ["93.184.216.34", "192.168.1.4"],
            "v6.example": ["2001:db8::1"],
            "bad.example": ["not-an-ip"],
        }[hostname]

    def test_public_destination_is_validated_without_network(self):
        destination = validate_destination("https://public.example/a", resolve=self.resolver)
        self.assertEqual(destination.hostname, "public.example")
        self.assertEqual(destination.port, 443)
        self.assertEqual(destination.addresses, ("93.184.216.34",))

    def test_private_reserved_and_mixed_dns_answers_fail_closed(self):
        for hostname in ("private.example", "mixed.example", "v6.example", "bad.example"):
            with self.subTest(hostname=hostname):
                with self.assertRaises(FetchPolicyError):
                    validate_destination(f"https://{hostname}/", resolve=self.resolver)

    def test_url_shape_rejects_credentials_non_http_and_bad_ports(self):
        for url in (
            "file:///etc/passwd",
            "https://user:password@public.example/",
            "https://public.example:99999/",
            "https://public.example/ bad",
        ):
            with self.subTest(url=url):
                with self.assertRaises(FetchPolicyError):
                    validate_destination(url, resolve=self.resolver)

    def test_malformed_ipv6_is_a_policy_error(self):
        with self.assertRaises(FetchPolicyError):
            validate_destination("https://[2001:db8::1/", resolve=self.resolver)

    def test_each_redirect_is_resolved_and_validated(self):
        chain = validate_redirect_chain(
            "https://public.example/start", ["/next"], resolve=self.resolver
        )
        self.assertEqual(chain[-1].url, "https://public.example/next")
        with self.assertRaises(FetchPolicyError):
            validate_redirect_chain(
                "https://public.example/start",
                ["https://private.example/secret"],
                resolve=self.resolver,
            )

    def test_redirect_limit_and_non_http_redirects_are_rejected(self):
        with self.assertRaises(FetchPolicyError):
            validate_redirect_chain(
                "https://public.example/start",
                ["/1", "/2", "/3"],
                resolve=self.resolver,
                max_redirects=2,
            )
        with self.assertRaises(FetchPolicyError):
            validate_redirect_chain(
                "https://public.example/start", ["javascript:alert(1)"],
                resolve=self.resolver,
            )
