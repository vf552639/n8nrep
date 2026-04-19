def test_configure_logging_smoke(tmp_path):
    from app.logging_config import configure_logging

    logf = tmp_path / "t.log"
    configure_logging(json_logs=False, level="INFO", log_file_path=str(logf))
    import logging

    logging.getLogger("test_logger").info("hello")
    assert logf.read_text().count("hello") >= 1
