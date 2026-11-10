# Run through the housekeeping controller as rods:
# /rules/tests/run_test.sh -r run_housekeeping -a "physical_files,async" -j
"""Report missing physical copies using one recursive iRODS iscan."""

import errno
import re
from subprocess import run  # nosec: argument list, never a shell


PROJECT_ROOT = "/nlmumc/projects/"
# iscan returns the iRODS status directly; POSIX keeps its low eight bits.
# UNIX_FILE_STAT_ERR is -516000 in iRODS 5.1.0.
MISSING_FILE_RETURN_CODE = (-516000 - errno.ENOENT) % 256
MISSING_FILE = re.compile(
    r"Physical file (?P<physical_path>/.+) on server (?P<host>\S+) is missing, "
    r"corresponding to iRODS object (?P<path>/.+)"
)


def _audit_physical_files(_ctx):
    stdout, stderr, return_code = "", "", None
    findings, errors = [], []
    try:
        completed = run(
            ["iscan", "-d", "-r", PROJECT_ROOT],
            capture_output=True, text=True, shell=False, check=False,
        )
    except OSError as error:
        errors.append("Could not start iscan: " + str(error))
    else:
        stdout, stderr, return_code = completed.stdout, completed.stderr, completed.returncode
        missing_messages = 0
        for line in stdout.splitlines():
            if not line.strip():
                continue
            match = MISSING_FILE.fullmatch(line)
            if not match:
                errors.append("Unexpected iscan output: " + line)
                continue
            missing_messages += 1
            finding = match.groupdict()
            if finding["path"].startswith(PROJECT_ROOT):
                findings.append(finding)
        if stderr.strip():
            errors.append("iscan stderr: " + stderr.strip())
        if return_code != 0 and not (return_code == MISSING_FILE_RETURN_CODE and missing_messages):
            errors.append(f"iscan exited with return code {return_code}")

    report = {
        "check": "physical_files", "execution_status": "failed" if errors else "completed",
        "summary": {"missing_physical_copies": len(findings),
                    "files_with_findings": len({entry["path"] for entry in findings}), "errors": len(errors)},
        "findings": findings, "stdout": stdout, "stderr": stderr, "return_code": return_code,
        "errors": errors,
    }
    if errors:
        report["error"] = "; ".join(errors)
    return report
