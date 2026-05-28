from src.tools.sandbox import run_code_in_sandbox


def test_sandbox_print():
    rc, out, err = run_code_in_sandbox("print('ok')", timeout=2)
    assert rc == 0
    assert "ok" in out


def test_sandbox_exit_code():
    rc, out, err = run_code_in_sandbox("import sys; sys.exit(3)", timeout=2)
    assert rc == 3
