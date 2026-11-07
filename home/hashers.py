from django.contrib.auth.hashers import Argon2PasswordHasher

from home.passwords import normalize_password


class SuperHarryArgon2PasswordHasher(Argon2PasswordHasher):
    # Owner-approved T027 profile (2026-11-06): 19 MiB, t=2, p=1.
    time_cost = 2
    memory_cost = 19456
    parallelism = 1
    hash_len = 32
    salt_len = 16

    def encode(self, password, salt):
        return super().encode(normalize_password(password), salt)

    def verify(self, password, encoded):
        return super().verify(normalize_password(password), encoded)
