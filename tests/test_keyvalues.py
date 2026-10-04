"""KeyValues syntax and compatibility contracts used by configuration editing."""
import unittest
import subprocess
import sys

from dolly import launcher


class KeyValuesTests(unittest.TestCase):
    def test_leaf_import_does_not_load_lifecycle_orchestrators(self):
        result = subprocess.run([sys.executable, '-c',
            'import sys; from dolly.keyvalues import _parse; '
            'assert _parse("key value")[0].value.value == "value"; '
            'assert not ({"dolly.launcher", "dolly.controller", '
            '"dolly.graphics_profiles", "dolly.session_cleanup"} & sys.modules.keys())'],
            capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_compatibility_exports_share_types_and_error_identity(self):
        from dolly import keyvalues, graphics_profiles, session_cleanup
        from dolly.launch_errors import LaunchError
        for name in ('_Token', '_Entry', '_tokens', '_parse', '_named'):
            self.assertIs(getattr(launcher, name), getattr(keyvalues, name))
        for module in (launcher, keyvalues, graphics_profiles, session_cleanup):
            self.assertIs(module.LaunchError, LaunchError)

    def test_offsets_include_conditions_but_not_following_comments(self):
        text = '\ufeff// header\r\nRoot { "key" "value" [$WIN32] [!$LINUX] /* tail */ }'
        root = launcher._parse(text)[0]
        entry = root.children[0]
        self.assertEqual(text[entry.key.start:entry.key.end], '"key"')
        self.assertEqual(text[entry.value.start:entry.value.end], '"value"')
        self.assertEqual(text[entry.key.start:entry.end], '"key" "value" [$WIN32] [!$LINUX]')
        self.assertEqual(text[root.opening.start:root.opening.end], '{')
        self.assertEqual(text[root.closing.start:root.end], '}')

    def test_duplicate_keys_are_preserved_and_named_lookup_is_case_insensitive(self):
        entries = launcher._parse('Game one GAME two Other three')
        matches = launcher._named(entries, 'game')
        self.assertEqual([entry.value.value for entry in matches], ['one', 'two'])
        self.assertIs(matches[0], entries[0])
        self.assertIs(matches[1], entries[1])

    def test_quoted_braces_comments_and_escapes_are_text(self):
        entries = launcher._parse(r'''"root" { "}" "a\"b\\c" text "// not /* a comment */" }''')
        self.assertEqual(entries[0].children[0].key.value, '}')
        self.assertEqual(entries[0].children[0].value.value, 'a"b\\c')
        self.assertEqual(entries[0].children[1].value.value, '// not /* a comment */')

    def test_empty_and_comment_only_documents(self):
        for text in ('', '\ufeff \t\r\n', '// no newline', '/* { ignored } */'):
            with self.subTest(text=text):
                self.assertEqual(launcher._tokens(text), [])
                self.assertEqual(launcher._parse(text), [])

    def test_malformed_documents_preserve_error_type_and_message(self):
        cases = {
            '/*': 'gameinfo.gi contains an unterminated block comment.',
            '"': 'gameinfo.gi contains an unterminated quoted value.',
            '[': 'gameinfo.gi contains an unterminated condition.',
            '}': 'gameinfo.gi has an unmatched closing brace.',
            '{': 'Unsupported gameinfo.gi key syntax.',
            'key': "gameinfo.gi ends before a key's value.",
            'key }': 'Unsupported gameinfo.gi value syntax.',
            'key {': 'gameinfo.gi has an unclosed block.',
        }
        for text, message in cases.items():
            with self.subTest(text=text):
                with self.assertRaises(launcher.LaunchError) as caught:
                    launcher._parse(text)
                self.assertIs(type(caught.exception), launcher.LaunchError)
                self.assertEqual(str(caught.exception), message)


if __name__ == '__main__':
    unittest.main()
