from pathlib import Path


def test_fastapi_profile_dependencies_are_installed_with_dumbbots() -> None:
    requirements = Path("requirements.txt").read_text(encoding="utf-8").splitlines()

    assert "fastapi==0.116.1" in requirements
    assert "httpx==0.28.1" in requirements
    assert "uvicorn==0.35.0" in requirements
