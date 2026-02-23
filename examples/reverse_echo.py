import sys


def main():
    print("Reverse Echo Bot started. Type something and press Enter.")
    while True:
        try:
            line = sys.stdin.readline()
            if not line:  # EOF
                break
            reversed_line = line.strip()[::-1]
            print(reversed_line)
            sys.stdout.flush()  # Ensure output is sent immediately
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            break


if __name__ == "__main__":
    main()
