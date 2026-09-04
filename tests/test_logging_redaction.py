from __future__ import annotations

import logging
import sys

from aegisvault.utils.logging import RedactingFormatter, redact_sensitive_text


def test_redactor_removes_secret_labels_tokens_and_local_paths() -> None:
    raw = (
        'password="hunter2" passphrase=correct-horse '
        "AGV1.QUdWVEVYVAEAAAB4 AK#bundled-key#Y2lwaGVydGV4dA== "
        r"path=C:\Users\Alice\Private Folder\secret.txt"
    )

    redacted = redact_sensitive_text(raw)

    for sensitive in ["hunter2", "correct-horse", "QUdWVEVYVAEAAAB4", "bundled-key", "Y2lwaGVydGV4dA", "Alice", "secret.txt"]:
        assert sensitive not in redacted
    assert "[REDACTED]" in redacted
    assert "[PATH]" in redacted


def test_formatter_redacts_parameterized_message_and_exception_text() -> None:
    try:
        raise ValueError("ciphertext=legacy-sensitive-value")
    except ValueError:
        record = logging.LogRecord(
            "aegisvault.test",
            logging.ERROR,
            __file__,
            1,
            "token=%s",
            ("AGV1.c2Vuc2l0aXZlLXRva2Vu",),
            exc_info=sys.exc_info(),
        )

    rendered = RedactingFormatter("%(levelname)s %(message)s").format(record)

    assert "c2Vuc2l0aXZlLXRva2Vu" not in rendered
    assert "legacy-sensitive-value" not in rendered
    assert rendered.count("[REDACTED]") >= 2
    assert record.exc_text is not None
    assert "legacy-sensitive-value" not in record.exc_text
