# T228: gateway credential configuration

The application resolves `OMNIROUTE_ENDPOINT`, `OMNIROUTE_EXTERNAL_MODEL` and
`OMNIROUTE_LOCAL_MODEL` without provider API keys. The web and chat worker
unit templates load `omniroute-api-key` as an encrypted systemd credential;
the Django and TOTP credentials retain their existing names. An explicitly
configured systemd credential directory fails closed when the gateway key is
missing. The environment key is available for development. The retired direct
provider-key loader rejects requests without disclosing credential values.

## Migration and rollback procedure

Before changing an installation, inventory the active units, endpoint, release
and protected credential references without printing secrets. Preserve a usable
previous release, its unit configuration and protected credential material in
their existing custody; do not copy keys into the application environment or
repository. Configure the gateway's provider credentials within the gateway,
provision its separate application credential using the host's protected
systemd credential mechanism, and set the gateway endpoint and model names in
the approved service configuration. Preserve Django, TOTP and TLS custody.
Verify service startup, gateway authentication and a permitted application flow
before retiring old credential paths. Do not delete the rollback material until
the applicable operational retention and acceptance decisions are satisfied.

If validation fails, stop admission and the worker, restore the prior release
and its matching service configuration and protected credential references,
then restart and verify that release according to the deployment runbook.
Do not introduce direct provider keys into the new release as a fallback. This
is a procedure, not evidence of a migration or rollback exercise.

## Validation and boundaries

On 2026-11-14, `python manage.py test home.test_provider_credentials
home.test_provider_availability home.test_runtime_config` passed 31 tests,
10 skipped; `python -m pytest -q tests/test_t228_configuration.py` passed six
tests. These use synthetic credentials and do not verify installed credentials.
T229 owns the remaining durable gateway dispatch and local inference routing;
legacy dispatch code remains present, with its direct credential loader retired.
T241 covers broader gateway/provider acceptance and T245 operational recovery.
No deployment, live credential migration, rollback or production acceptance is
claimed by this record.
