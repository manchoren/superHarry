import os
import stat
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured


_SYSTEMD_CREDENTIAL_NAMES = frozenset(
    {"django-secret", "totp-aes256-key", "omniroute-api-key"}
)


def _open_private_file(
    path: str,
    *,
    allowed_systemd_name: str | None = None,
    enforce_mode_on_all_platforms: bool = False,
) -> int:
    if not os.path.isabs(path):
        raise OSError("credential path is not absolute")
    descriptor = os.open(
        path,
        os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_BINARY", 0),
    )
    try:
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode):
            raise OSError("credential is not a regular file")
        mode = stat.S_IMODE(metadata.st_mode)
        if (os.name == "posix" or enforce_mode_on_all_platforms) and mode & 0o077:
            # systemd credentials are deliberately read-only (0440) and use a
            # per-unit ACL to grant access to the configured service user.
            # Accept that representation only under systemd's runtime path.
            credential_directory = os.environ.get("CREDENTIALS_DIRECTORY", "")
            expected_directory = f"/run/credentials/{Path(credential_directory).name}"
            permitted = (
                allowed_systemd_name in _SYSTEMD_CREDENTIAL_NAMES
                and credential_directory == expected_directory
                and Path(credential_directory).name.endswith(".service")
                and os.path.realpath(path)
                == os.path.join(credential_directory, allowed_systemd_name)
                and mode == 0o440
                and not mode & 0o022
                and metadata.st_uid == 0
                and metadata.st_gid == 0
            )
            directory_metadata = (
                os.stat(credential_directory, follow_symlinks=False)
                if permitted
                else None
            )
            permitted = bool(
                permitted
                and directory_metadata
                and stat.S_ISDIR(directory_metadata.st_mode)
                and directory_metadata.st_uid == 0
                and directory_metadata.st_gid == 0
                and not stat.S_IMODE(directory_metadata.st_mode) & 0o027
            )
            if not permitted:
                raise OSError("credential permissions are not private")
        return descriptor
    except BaseException:
        os.close(descriptor)
        raise


def open_systemd_credential(name: str) -> int:
    if name not in _SYSTEMD_CREDENTIAL_NAMES:
        raise OSError("unknown systemd credential")
    directory = os.environ.get("CREDENTIALS_DIRECTORY", "")
    if (
        not directory
        or not os.path.isabs(directory)
    ):
        raise OSError("systemd credentials directory is unavailable")
    return _open_private_file(
        os.path.join(directory, name),
        allowed_systemd_name=name,
        enforce_mode_on_all_platforms=True,
    )


def read_service_secret(path: str) -> str:
    if not os.path.isabs(path):
        raise ImproperlyConfigured("The service secret path must be absolute.")

    try:
        systemd_path = os.path.join(os.environ.get("CREDENTIALS_DIRECTORY", ""), "django-secret")
        descriptor = (
            open_systemd_credential("django-secret")
            if path == systemd_path
            else _open_private_file(path)
        )
        try:
            secret_parts = bytearray()
            while len(secret_parts) < 129:
                chunk = os.read(descriptor, 129 - len(secret_parts))
                if not chunk:
                    break
                secret_parts.extend(chunk)
            secret = bytes(secret_parts)
        finally:
            os.close(descriptor)
    except OSError as exc:
        raise ImproperlyConfigured("The service secret file is unavailable.") from exc

    if len(secret) < 50 or len(secret) > 128 or b"\n" in secret or b"\r" in secret:
        raise ImproperlyConfigured("The service secret file is invalid.")
    try:
        return secret.decode("ascii")
    except UnicodeDecodeError as exc:
        raise ImproperlyConfigured("The service secret file is invalid.") from exc
