__author__ = "Jérôme Louradour"
__credits__ = ["Jérôme Louradour"]
__license__ = "MIT"

import unittest
import sys, os
import subprocess
import shutil
import tempfile
import json

FAIL_IF_REFERENCE_NOT_FOUND = True
GENERATE_NEW_ONLY = False
GENERATE_ALL = False

class TestHelper(unittest.TestCase):

    def setUp(self):
        self.maxDiff = None
        self.createdReferences = []

    def tearDown(self):
        if GENERATE_ALL or GENERATE_NEW_ONLY or not FAIL_IF_REFERENCE_NOT_FOUND:
            if len(self.createdReferences) > 0:
                print("WARNING: Created references: " + ", ".join(self.createdReferences).replace(self.get_data_path()+"/", ""))
        else:
            self.assertEqual(self.createdReferences, [], "Created references: " + ", ".join(self.createdReferences).replace(self.get_data_path()+"/", ""))
    
    def get_main_path(self, fn = None):
        return self._get_path("whisper_timestamped", fn)

    def get_output_path(self, fn = None):
        if fn == None: return tempfile.gettempdir()
        return os.path.join(tempfile.gettempdir(), fn)

    def get_expected_path(self, fn = None, check = False):
        return self._get_path("tests/expected", fn, check = check)

    def get_data_files(self, files = None):
        return [self.get_data_path(fn)
            for fn in (sorted(os.listdir(self.get_data_path()) if files is None else files))]

    def get_generated_files(self, input_filename, output_path):
        for ext in ["txt", "srt", "vtt", "words.srt", "words.vtt", "words.json"]:
            yield os.path.join(output_path, os.path.basename(input_filename) + "." + ext)

    def assertRun(self, cmd):
        if isinstance(cmd, str):
            return self.assertRun(cmd.split())
        curdir = os.getcwd()
        os.chdir(tempfile.gettempdir())
        if cmd[0].endswith(".py"):
            cmd = [sys.executable] + cmd
        print("Running:", " ".join(cmd))
        p = subprocess.Popen(cmd, 
            env = dict(os.environ, PYTHONPATH = os.pathsep.join(sys.path)), # Otherwise ".local" path might be missing
            stdout = subprocess.PIPE, stderr = subprocess.PIPE
        )
        os.chdir(curdir)
        (stdout, stderr) = p.communicate()
        self.assertEqual(p.returncode, 0, msg = stderr.decode("utf-8"))
        return (stdout.decode("utf-8"), stderr.decode("utf-8"))

    def assertNonRegression(self, content, reference):
        """
        Check that a file/folder is the same as a reference file/folder.
        """
        self.assertTrue(os.path.exists(content), f"Missing file: {content}")
        is_file = os.path.isfile(reference) if os.path.exists(reference) else os.path.isfile(content)

        reference = self.get_expected_path(reference, check = FAIL_IF_REFERENCE_NOT_FOUND)
        if not os.path.exists(reference) or GENERATE_ALL:
            dirname = os.path.dirname(reference)
            if not os.path.isdir(dirname):
                os.makedirs(dirname)
            if is_file:
                shutil.copyfile(content, reference)
            else:
                shutil.copytree(content, reference)
            self.createdReferences.append(reference)

        if is_file:
            self.assertTrue(os.path.isfile(content))
            self._check_file_non_regression(content, reference)
        else:
            self.assertTrue(os.path.isdir(content))
            for root, dirs, files in os.walk(content):
                for f in files:
                    f_ref = os.path.join(reference, f)
                    self.assertTrue(os.path.isfile(f_ref), f"Additional file: {f}")
                    self._check_file_non_regression(os.path.join(root, f), f_ref)
            for root, dirs, files in os.walk(reference):
                for f in files:
                    f = os.path.join(content, f)
                    self.assertTrue(os.path.isfile(f), f"Missing file: {f}")

    def get_data_path(self, fn = None, check = True):
        return self._get_path("tests/data", fn, check)

    def _get_path(self, prefix, fn = None, check = True):
        path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            prefix
        )
        if fn:
            path = os.path.join(path, fn)
        if check:
            self.assertTrue(os.path.exists(path), f"Cannot find {path}")
        return path

    def _check_file_non_regression(self, file, reference):
        if file.endswith(".json"):
            import json
            with open(file) as f:
                content = json.load(f)
            with open(reference) as f:
                reference_content = json.load(f)
            self.assertClose(content, reference_content, msg = f"File {file} does not match reference {reference}")
            return
        with open(file) as f:
            content = f.readlines()
        with open(reference) as f:
            reference_content = f.readlines()
        self.assertEqual(content, reference_content, msg = f"File {file} does not match reference {reference}")        

    def assertClose(self, obj1, obj2, msg = None):
        return self.assertEqual(self.loose(obj1), self.loose(obj2), msg = msg)

    def loose(self, obj):
        # Return an approximative value of an object
        if isinstance(obj, list):
            return [self.loose(a) for a in obj]
        if isinstance(obj, float):
            f = round(obj, 1)
            return 0.0 if f == -0.0 else f
        if isinstance(obj, dict):
            return {k: self.loose(v) for k, v in obj.items()}
        if isinstance(obj, tuple):
            return tuple(self.loose(list(obj)))
        if isinstance(obj, set):
            return self.loose(list(obj), "set")
        return obj

    def get_audio_duration(self, audio_file):
        # Get the duration in sec *without introducing additional dependencies*
        import whisper
        return len(whisper.load_audio(audio_file)) / whisper.audio.SAMPLE_RATE

    def get_device_str(self):
        import torch
        return "cpu" if not torch.cuda.is_available() else "cuda"

class TestPythonImport(TestHelper):

    def test_python_import(self):

        try:
            import whisper_timestamped
        except ModuleNotFoundError:
            sys.path.append(os.path.realpath(os.path.dirname(os.path.dirname(__file__))))
            import whisper_timestamped

        model = whisper_timestamped.load_model("tiny")

        res = whisper_timestamped.transcribe(model, self.get_data_path("bonjour.wav"))

        expected = json.load(open(self.get_expected_path("tiny_auto/bonjour.wav.words.json", check = True)))

        self.assertClose(res, expected)


class TestTranscribeCli(TestHelper):

    def test_cli_tiny_auto(self):
        self._test_cli_(
            ["--model", "tiny"],
            "tiny_auto"
        )

    def test_cli_tiny_fr(self):
        self._test_cli_(
            ["--model", "tiny", "--language", "fr"],
            "tiny_fr"
        )

    def test_cli_medium_auto(self):
        self._test_cli_(
            ["--model", "medium"],
            "medium_auto"
        )

    def test_cli_medium_fr(self):
        self._test_cli_(
            ["--model", "medium", "--language", "fr"],
            "medium_fr"
        )

    def _test_cli_(self, opts, name, files = None):

        output_dir = self.get_output_path(name)

        for input_filename in self.get_data_files(files):

            # Butterfly effect: Results are different depending on the device for long files
            duration = self.get_audio_duration(input_filename)
            device_dependent = duration > 60 or (duration > 30 and "tiny_fr" in name)
            def ref_name(output_filename):
                return name + (f".{self.get_device_str()}" if device_dependent else "")+ "/" + os.path.basename(output_filename)

            if GENERATE_NEW_ONLY:
                if min([os.path.exists(self.get_expected_path(ref_name(output_filename)))
                    for output_filename in self.get_generated_files(input_filename, output_dir)]):
                    print("Output already exists, skipping", input_filename)
                    continue
            (stdout, stderr) = self.assertRun([
                self.get_main_path("transcribe.py"),
                input_filename,
                "--output_dir", output_dir,
                "--json", "True",
                *opts,
            ])
            print(stdout)
            print(stderr)
            for output_filename in self.get_generated_files(input_filename, output_dir):
                self.assertNonRegression(output_filename, ref_name(output_filename))

        shutil.rmtree(output_dir, ignore_errors = True)
