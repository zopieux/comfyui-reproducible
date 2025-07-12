#!/usr/bin/env nix-shell
#!nix-shell -i python -p python3

from pathlib import PurePath
import sys
import os


def split_syscall_args(args_string):
  args = []
  current_arg = ""
  bracket_level = 0
  in_quote = False

  # Handle argument lists truncated by strace (e.g., "arg1, ...")
  if args_string.endswith('...'):
    args_string = args_string[:-3].strip()

  for char in args_string:
    # The split happens on commas that are not inside quotes or brackets.
    if char == ',' and not in_quote and bracket_level == 0:
      args.append(current_arg.strip())
      current_arg = ""
    else:
      # Accumulate the character and update state.
      current_arg += char
      if char == '"':
        # This simple toggle is sufficient as strace doesn't use escaped quotes.
        in_quote = not in_quote
      elif char == '[' and not in_quote:
        bracket_level += 1
      elif char == ']' and not in_quote:
        bracket_level -= 1

  # Add the last argument to the list.
  if current_arg:
    args.append(current_arg.strip())

  return args


def parse_strace_log(file_path):
  """
  Parses an strace log file and yields (path, is_success_str) tuples.
  """
  try:
    with open(file_path, 'r', encoding='utf-8') as f:
      for line in f:
        # A syscall line typically looks like: `syscall(...) = result`.
        # We split on the last occurrence of ') = ' to handle nested parentheses.
        try:
          pre, post = line.rsplit(') = ', 1)
        except ValueError:
          continue  # Not a syscall line, e.g., '--- SIGINT ---' or '+++ exited +++'

        # Find the start of the arguments within the 'pre' part.
        try:
          # The part before the first '(' is the syscall name and PID.
          args_string = pre.split('(', 1)[1]
        except IndexError:
          continue  # Malformed line

        # Determine if the call was successful.
        # Failures start with '-1' followed by an error code (e.g., ENOENT).
        result_str = post.strip()
        is_success = not result_str.startswith('-1')

        # Extract path arguments from the parsed argument list.
        syscall_args = split_syscall_args(args_string)
        for arg in syscall_args:
          # A path argument is a quoted string. It might be truncated by strace.
          if arg.startswith('"'):
            # Strip the leading quote.
            path = arg[1:]

            # If the string is not truncated, strip the trailing quote.
            if path.endswith('"'):
              path = path[:-1]

            # strace can also truncate the path itself with '...'.
            if path.endswith('...'):
              path = path[:-3]

            if path:  # Ensure we don't yield an empty path.
              yield path, is_success

  except FileNotFoundError:
    print(f"Error: File not found at {file_path}", file=sys.stderr)
    sys.exit(1)
  except Exception as e:
    print(f"An error occurred: {e}", file=sys.stderr)
    sys.exit(1)


def main():
  if len(sys.argv) != 2:
    print(f"Usage: {sys.argv[0]} <strace_log_file>", file=sys.stderr)
    sys.exit(1)

  log_file = sys.argv[1]

  for path, success in parse_strace_log(log_file):
    if not success:
      continue
    path = PurePath(os.path.normpath(path))
    if not path.is_absolute():
      continue
    print(str(path))


if __name__ == "__main__":
  main()
