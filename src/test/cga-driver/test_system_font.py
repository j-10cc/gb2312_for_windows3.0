"""Check actual FONT bytes and all defined GB2312 pair widths."""
from pathlib import Path
import struct
import sys
import unittest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'src/main/cga-driver'))
from build_cga_system_font import gb2312_metrics


class SystemFontTest(unittest.TestCase):
    def test_only_gb_byte_widths_change(self):
        original = (ROOT/'external/win30ddk/fonts/system/ega/egasys.fnt').read_bytes()
        result = gb2312_metrics(original)
        first = original[95]
        allowed = {118+4*(code-first)+i for code in range(0xA1,0xFF) for i in (0,1)}
        self.assertEqual(len(original),len(result))
        self.assertTrue(all(a==b or i in allowed for i,(a,b) in enumerate(zip(original,result))))
        valid=0
        for lead in range(0xA1,0xF8):
            for trail in range(0xA1,0xFF):
                try:bytes((lead,trail)).decode('gb2312')
                except UnicodeDecodeError:continue
                widths=[struct.unpack_from('<H',result,118+4*(code-first))[0] for code in (lead,trail)]
                self.assertEqual(widths,[8,8])
                valid+=1
        self.assertEqual(valid,7445)
        self.assertEqual(gb2312_metrics(result),result)

    def test_fixed_pitch_is_rejected(self):
        font=bytearray((ROOT/'external/win30ddk/fonts/system/ega/egasys.fnt').read_bytes())
        struct.pack_into('<H',font,86,8)
        with self.assertRaises(ValueError):gb2312_metrics(bytes(font))


if __name__ == '__main__':unittest.main()
