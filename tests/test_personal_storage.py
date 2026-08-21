import pytest

from cakrawala.personal.storage import list_portfolio_transactions


def test_personal_storage_requires_database_url() -> None:
    with pytest.raises(ValueError, match="database_url is required"):
        list_portfolio_transactions("", "owner-sub")


def test_personal_storage_requires_owner_subject() -> None:
    with pytest.raises(ValueError, match="owner_sub is invalid"):
        list_portfolio_transactions("postgresql://example.invalid/db", "")


def test_personal_storage_bounds_result_limit() -> None:
    with pytest.raises(ValueError, match="limit must be between 1 and 100"):
        list_portfolio_transactions(
            "postgresql://example.invalid/db",
            "owner-sub",
            limit=101,
        )
