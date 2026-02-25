from gramit.cli import GramitCLI

def test_enter_flag_default():
    cli = GramitCLI()
    parser = cli.get_parser()
    args = parser.parse_args(["--chat-id", "123", "ls"])
    assert args.enter is False

def test_enter_flag_explicit():
    cli = GramitCLI()
    parser = cli.get_parser()
    args = parser.parse_args(["-e", "--chat-id", "123", "ls"])
    assert args.enter is True

def test_no_enter_flag():
    cli = GramitCLI()
    parser = cli.get_parser()
    # Explicitly disable
    args = parser.parse_args(["--no-enter", "--chat-id", "123", "ls"])
    assert args.enter is False

def test_abbreviated_enter_flag():
    cli = GramitCLI()
    parser = cli.get_parser()
    # Testing both explicit --e and abbreviation
    args = parser.parse_args(["--e", "--chat-id", "123", "ls"])
    assert args.enter is True

def test_log_file_argument():
    cli = GramitCLI()
    parser = cli.get_parser()
    # Test default
    args = parser.parse_args(["--chat-id", "123", "ls"])
    assert args.log_file == "gramit.log"
    
    # Test custom
    args = parser.parse_args(["--log-file", "test.log", "--chat-id", "123", "ls"])
    assert args.log_file == "test.log"
