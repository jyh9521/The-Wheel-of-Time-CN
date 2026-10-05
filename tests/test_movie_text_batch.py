import json
import struct
import tempfile
import unittest
from pathlib import Path

from tools.pack.movie_text import rebuild, text_tables, read_translations, wrap
from tools.pack.movie_text_probe import sha, restore


def atom(kind,body):return struct.pack('>I4s',len(body)+8,kind)+body


def fixture(two_descriptions=False):
    text=[b'\x00\x05Hello',b'\x00\x01 ',b'\x00\x05World']
    header=bytearray(84);header[3]=14;struct.pack_into('>I',header,12,3)
    struct.pack_into('>II',header,76,640<<16,20<<16)
    tkhd=atom(b'tkhd',header);mdhd=bytearray(24);struct.pack_into('>I',mdhd,12,600)
    desc=bytearray(57);desc[6:8]=b'\x00\x01';struct.pack_into('>hhhh',desc,22,0,0,20,640)
    desc[-7:]=b'\x06Geneva';description=atom(b'text',desc)
    def moov(offset):
        stsd=atom(b'stsd',struct.pack('>II',0,2 if two_descriptions else 1)+description*(2 if two_descriptions else 1))
        stsz=atom(b'stsz',struct.pack('>III3I',0,0,3,*map(len,text)))
        stco=atom(b'stco',struct.pack('>II3I',0,3,offset,offset+7,offset+10))
        runs=[1,1,1,1] if not two_descriptions else [2,1,1,1,3,1,2]
        stsc=atom(b'stsc',struct.pack('>'+'I'*(1+len(runs)),0,*runs))
        stts=atom(b'stts',struct.pack('>IIII',0,1,3,600))
        stbl=atom(b'stbl',stsd+stsz+stco+stsc+stts)
        return atom(b'moov',atom(b'trak',tkhd+atom(b'mdia',atom(b'mdhd',mdhd)+atom(b'hdlr',bytes(4)+b'mhlrtext')+atom(b'minf',stbl))))
    preliminary=moov(0);return moov(len(preliminary)+8)+atom(b'mdat',b''.join(text))


class MovieBatchTests(unittest.TestCase):
    def setup_input(self,two=False):
        data=fixture(two);t=text_tables(data)
        profile=dict(sha256=sha(data),size=len(data),track_id=3,samples=[{k:s[k] for k in ('index','sha256','nonempty','begin','duration')} for s in t['samples']])
        return data,profile,dict(source_font='Geneva',font='SimHei',media_language=33,line_units=44,track_height=44)

    def test_all_samples_and_blank_clock(self):
        data,p,c=self.setup_input();new,diff=rebuild(data,p,{0:'新游戏',2:'第二句话。'},c)
        samples=text_tables(new)['samples']
        self.assertEqual([s['text'] for s in samples],['新游戏','','第二句话。'])
        self.assertEqual([s['begin'] for s in samples],[0,1,2])
        self.assertEqual(restore(new,diff),data)

    def test_description_transition(self):
        data,p,c=self.setup_input(True);new,diff=rebuild(data,p,{0:'中文',2:'对白'},c)
        self.assertEqual(restore(new,diff),data)
        self.assertEqual(new.count(b'SimHei'),2)

    def test_wrong_version(self):
        data,p,c=self.setup_input()
        with self.assertRaisesRegex(ValueError,'Unknown'):rebuild(data+b'x',p,{0:'中',2:'文'},c)

    def test_missing_and_extra_translation(self):
        data,p,c=self.setup_input()
        for rows in ({0:'中'},{0:'中',1:'不应显示',2:'文'}):
            with self.assertRaisesRegex(ValueError,'Missing'):rebuild(data,p,rows,c)

    def test_sample_hash_gate(self):
        data,p,c=self.setup_input();p['samples'][0]['sha256']='0'*64
        with self.assertRaisesRegex(ValueError,'identity'):rebuild(data,p,{0:'中',2:'文'},c)

    def test_wrap_punctuation(self):
        self.assertEqual(wrap('汉字汉字。汉字',4),'汉字汉字。\r汉字')
        with self.assertRaisesRegex(ValueError,'two-line'):wrap('中'*100)

    def test_duplicate_id(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'strings.tsv';p.write_text('0\t中文\n0\t重复\n','utf8')
            with self.assertRaisesRegex(ValueError,'Duplicate'):read_translations(p)

    def test_rollback_tamper(self):
        data,p,c=self.setup_input();new,diff=rebuild(data,p,{0:'中',2:'文'},c)
        with self.assertRaisesRegex(ValueError,'identity'):restore(new[:-1],diff)


if __name__=='__main__':unittest.main()
