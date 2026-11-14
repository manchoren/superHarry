from unittest import TestCase
from unittest.mock import MagicMock, patch

from home.gemini_dispatch import GeminiDispatchError, dispatch_gemini
from home.gemini_transport import GeminiTransport


class GeminiCountBoundaryTests(TestCase):
    def test_unverified_count_admission_blocks_all_provider_requests(self):
        transport = MagicMock()
        with self.assertRaises(GeminiDispatchError):
            dispatch_gemini(user_request='synthetic', principal_id='synthetic-user',
                            transport=transport, authorize=lambda: True, cancelled=lambda: False)
        transport.count.assert_not_called()
        transport.generate.assert_not_called()

    @patch('home.gemini_dispatch._require_gemini_count_admission')
    def test_count_rejection_prevents_generation(self, _admission):
        connection = MagicMock()
        connection.getresponse.return_value.status = 404
        transport = GeminiTransport('synthetic-key', timeout=3)

        with patch(
            'home.gemini_transport.http.client.HTTPSConnection',
            return_value=connection,
        ):
            with self.assertRaises(GeminiDispatchError) as error:
                dispatch_gemini(
                    user_request='synthetic request',
                    principal_id='synthetic-user',
                    transport=transport,
                    authorize=lambda: True,
                    cancelled=lambda: False,
                )

        self.assertNotIn('synthetic-key', str(error.exception))
        connection.request.assert_called_once()
        self.assertTrue(connection.request.call_args.args[1].endswith(':countTokens'))
        connection.close.assert_called_once()
