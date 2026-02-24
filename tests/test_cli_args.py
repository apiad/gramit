from gramit.cli import get_parser

def test_enter_flag_default():
    parser = get_parser()
    args = parser.parse_args(["--chat-id", "123", "ls"])
    assert args.enter is False

def test_enter_flag_explicit():
    parser = get_parser()
    args = parser.parse_args(["-e", "--chat-id", "123", "ls"])
    assert args.enter is True

def test_no_enter_flag():
    parser = get_parser()
    # Explicitly disable
    args = parser.parse_args(["--no-enter", "--chat-id", "123", "ls"])
    assert args.enter is False

def test_abbreviated_enter_flag():
    parser = get_parser()
    # Testing both explicit --e and abbreviation
    args = parser.parse_args(["--e", "--chat-id", "123", "ls"])
    assert args.enter is True
