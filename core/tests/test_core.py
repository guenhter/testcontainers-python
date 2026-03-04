import tempfile
from pathlib import Path

from testcontainers.core.container import DockerContainer


def test_garbage_collection_is_defensive():
    # For more info, see https://github.com/testcontainers/testcontainers-python/issues/399
    # we simulate garbage collection: start, stop, then call `del`
    container = DockerContainer("postgres:latest")
    container.start()
    container.stop(force=True, delete_volume=True)
    delattr(container, "_container")
    del container


def test_get_logs():
    with DockerContainer("hello-world") as container:
        stdout, stderr = container.get_logs()
        assert isinstance(stdout, bytes)
        assert isinstance(stderr, bytes)
        assert "Hello from Docker".encode() in stdout, "There should be something on stdout"


def test_docker_container_with_env_file():
    """Test that environment variables can be loaded from a file"""
    with tempfile.TemporaryDirectory() as temp_directory:
        env_file_path = Path(temp_directory) / "env_file"
        with open(env_file_path, "w") as f:
            f.write(
                """
                TEST_ENV_VAR=hello
                NUMBER=123
                DOMAIN=example.org
                ADMIN_EMAIL=admin@${DOMAIN}
                ROOT_URL=${DOMAIN}/app
                """
            )
        container = DockerContainer("alpine").with_command("tail -f /dev/null")  # Keep the container running
        container.with_env_file(env_file_path)  # Load the environment variables from the file
        with container:
            output = container.exec("env").output.decode("utf-8").strip()
            assert "TEST_ENV_VAR=hello" in output
            assert "NUMBER=123" in output
            assert "DOMAIN=example.org" in output
            assert "ADMIN_EMAIL=admin@example.org" in output
            assert "ROOT_URL=example.org/app" in output
            print(output)


# ---------------------------------------------------------------------------
# with_copy_to
# ---------------------------------------------------------------------------


def test_with_copy_to_bytes():
    """Bytes passed to with_copy_to should be readable inside the running container."""
    with (
        DockerContainer("alpine")
        .with_command(["cat", "/tmp/hello.txt"])
        .with_copy_to("/tmp/hello.txt", b"hello from bytes") as c
    ):
        c.wait()
        stdout, _ = c.get_logs()
        assert stdout.decode() == "hello from bytes"


def test_with_copy_to_file(tmp_path: Path):
    """A local file passed to with_copy_to should be readable inside the running container."""
    src = tmp_path / "copied.txt"
    src.write_bytes(b"hello from file")

    with DockerContainer("alpine").with_command(["cat", "/tmp/copied.txt"]).with_copy_to("/tmp/copied.txt", src) as c:
        c.wait()
        stdout, _ = c.get_logs()
        assert stdout.decode() == "hello from file"


def test_with_copy_to_directory(tmp_path: Path):
    """A local directory passed to with_copy_to should be readable inside the running container."""
    (tmp_path / "a.txt").write_text("aaa")
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "b.txt").write_text("bbb")

    with (
        DockerContainer("alpine")
        .with_command(["sh", "-c", "cat /mydata/a.txt && cat /mydata/sub/b.txt"])
        .with_copy_to("/mydata", tmp_path)
    ) as c:
        c.wait()
        stdout, _ = c.get_logs()
        output = stdout.decode()
        assert "aaa" in output
        assert "bbb" in output
