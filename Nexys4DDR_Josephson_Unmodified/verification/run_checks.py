"""Run from anywhere: python verification/run_checks.py (Icarus in PATH)."""
import hashlib
import pathlib
import shutil
import subprocess
import tempfile

root = pathlib.Path(__file__).resolve().parents[1]
for line in (root / 'verification/original_sha256.txt').read_text().splitlines():
    digest, name = line.split(maxsplit=1)
    assert hashlib.sha256((root / name).read_bytes()).hexdigest() == digest, name
print('PASS: original file SHA-256 checks')
iv, vvp = shutil.which('iverilog'), shutil.which('vvp')
if not iv or not vvp:
    raise SystemExit('Install Icarus Verilog and add iverilog/vvp to PATH, or use Vivado simulation.')
with tempfile.TemporaryDirectory() as temp:
    for top, sources in [
        ('tb_board_ui', ['original/jj_rcsj.sv', 'board/jj_board_ui.sv', 'verification/tb_board_ui.sv']),
        ('tb_jj', ['original/jj_rcsj.sv', 'original/tb_jj.sv']),
    ]:
        exe = str(pathlib.Path(temp) / (top + '.vvp'))
        subprocess.run([iv, '-g2012', '-s', top, '-o', exe] +
                       [str(root / s) for s in sources], check=True)
        result = subprocess.run([vvp, exe], check=True, capture_output=True, text=True)
        print(result.stdout)
        if top == 'tb_jj':
            rows = [line for line in result.stdout.splitlines() if ',' in line and line[0] in '-0123456789']
            assert len(rows) == 82, f'Expected 82 measurement rows, got {len(rows)}'
print('PASS: simulation checks completed')
