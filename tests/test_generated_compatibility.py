"""Reviewed data generation must preserve gates and refuse incomplete evidence."""
from copy import deepcopy
import json
from pathlib import Path
import re
import shutil
import struct
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import generate_compatibility as generate


class GeneratedCompatibilityTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.root = Path(folder.name)
        shutil.copytree(ROOT / 'native/profiles', self.root / 'native/profiles')
        (self.root / 'dolly').mkdir()
        for name in ('preload','replay_camera','follow_capabilities','follow_target'):
            shutil.copy2(ROOT/'dolly'/f'{name}.py', self.root/'dolly'/f'{name}.py')
        self.path = self.root / generate.CONTRACT
        self.data = generate.read_json(self.path)

    def save(self):
        self.path.write_text(json.dumps(self.data),encoding='utf-8')

    def test_repository_generated_files_are_current_without_game_access(self):
        with patch.object(generate.camera,'Image',side_effect=AssertionError('No game binary needed')):
            generate.check_generated(ROOT)

    def test_saved_reviews_round_trip_and_keep_every_existing_camera_profile(self):
        before = (self.root/'native/profiles/manifest.json').read_bytes()
        outputs = generate.generated_outputs(self.root)
        for name,text in outputs.items():
            path = self.root/name
            path.parent.mkdir(parents=True,exist_ok=True)
            path.write_text(text,encoding='utf-8')
        generate.check_generated(self.root)
        manifest = json.loads(before)
        for digest in manifest['modules']['citadel/bin/win64/client.dll']['accepted']:
            self.assertIn(digest,outputs['native/src/dolly_compat_generated.hpp'])
        self.assertEqual(before,(self.root/'native/profiles/manifest.json').read_bytes())
        path = self.root/'dolly/_runtime_generated.py'
        path.write_text(path.read_text()+'# stale edit\n',encoding='utf-8')
        with self.assertRaisesRegex(generate.ContractError,'drift'):
            generate.check_generated(self.root)

    def test_unlisted_client_profile_cannot_silently_extend_native_support(self):
        before = generate.generated_outputs(self.root)
        (self.root/'native/profiles/unreviewed-client.json').write_text(json.dumps({
            'client':{'client_sha256':'f'*64,'main_view_setup_rva':'0x100'}}))
        self.assertEqual(before,generate.generated_outputs(self.root))

    def test_unknown_module_fingerprint_is_rejected_before_emission(self):
        p=self.root/'native/profiles'/self.data['modules']['client']['profile']
        profile=generate.read_json(p)
        profile['client']['client_sha256']='f'*64
        p.write_text(json.dumps(profile))
        with self.assertRaisesRegex(generate.ContractError,'already be reviewed'):
            generate.generated_outputs(self.root)

    def test_older_camera_support_does_not_widen_preload_support(self):
        self.data['modules']['client']['profile']='deadlock-2026-09-30-6726-complete.json'
        self.save()
        with self.assertRaisesRegex(generate.ContractError,'preload pin'):
            generate.generated_outputs(self.root)

    def test_named_field_cannot_drift_from_saved_getters(self):
        self.data['schema']['C_BasePlayerPawn.m_pObserverServices']['offset']='0xe40'
        self.save()
        with self.assertRaisesRegex(generate.ContractError,'saved stock getter'):
            generate.generated_outputs(self.root)

    def test_schema_proof_must_be_part_of_the_actual_runtime_code_audit(self):
        spans=self.data['groups']['FollowTarget']['TARGET_SPANS']['value']
        next(row for row in spans if row['rva']=='0x815ee0')['sha256']='0'*64
        self.save()
        with self.assertRaisesRegex(generate.ContractError,'runtime code audit'):
            generate.generated_outputs(self.root)

    def test_missing_consumer_symbol_fails_before_any_output(self):
        del self.data['groups']['FollowTarget']['ENTITY_LIST']
        self.save()
        with self.assertRaisesRegex(generate.ContractError,'missing symbols'):
            generate.generated_outputs(self.root)
        self.assertFalse((self.root/'dolly/_runtime_generated.py').exists())

    def test_out_of_range_code_span_and_unknown_value_kind_are_rejected(self):
        original=deepcopy(self.data)
        for changed in ({'kind':'guessed','module':'client','value':'0x40'},
                        {'kind':'rva','module':'client','value':'0x80000000'},
                        {'kind':'offset','module':'client','value':True}):
            self.data=deepcopy(original)
            self.data['groups']['FollowTarget']['ENTITY_LIST']=changed
            self.save()
            with self.subTest(changed=changed), self.assertRaises(generate.ContractError):
                generate.generated_outputs(self.root)

    def test_wire_order_and_required_flags_are_preserved(self):
        self.data['attach_wire_fields'][:2]=list(reversed(self.data['attach_wire_fields'][:2]))
        self.save()
        with self.assertRaisesRegex(generate.ContractError,'ABI field order'):
            generate.generated_outputs(self.root)
        self.data=generate.read_json(ROOT/generate.CONTRACT)
        self.data['attach_fields'][0]['required']='yes'
        self.save()
        with self.assertRaisesRegex(generate.ContractError,'required/optional'):
            generate.generated_outputs(self.root)

    def test_retained_anchor_bytes_round_trip_without_new_profiles(self):
        outputs=generate.generated_outputs(self.root)
        header=outputs['native/src/dolly_follow_anchor_generated.hpp']
        arrays=re.findall(r'constexpr unsigned char kFollowCode(\d+)_([0-9a-f]+)\[\] = \{(.*?)\};',header,re.S)
        actual={(build,int(rva,16)):bytes(int(v,16) for v in re.findall(r'0x([0-9a-f]+)',body))
                for build,rva,body in arrays}
        expected={(a['build'],int(span['rva'],16)):bytes.fromhex(span['bytes'])
                  for a in self.data['follow_anchors'] for span in a['spans']}
        self.assertEqual(actual,expected)
        self.assertEqual({a['build'] for a in self.data['follow_anchors']},{'6722','6723','6726'})
        self.assertTrue(all(a['values']['observer_services_offset']=='0xe40' for a in self.data['follow_anchors']))

    def test_incomplete_or_duplicate_anchor_profiles_cannot_emit_hooks(self):
        original=deepcopy(self.data)
        self.data['follow_anchors'].append(deepcopy(self.data['follow_anchors'][0]))
        self.save()
        with self.assertRaisesRegex(generate.ContractError,'Duplicate'):
            generate.generated_outputs(self.root)
        self.data=original
        self.data['follow_anchors'][0]['spans']=[]
        self.save()
        with self.assertRaisesRegex(generate.ContractError,'exact code evidence'):
            generate.generated_outputs(self.root)

    def test_duplicate_json_keys_are_not_silently_overwritten(self):
        self.path.write_text('{"format":1,"format":2}')
        with self.assertRaisesRegex(generate.ContractError,'Duplicate JSON key'):
            generate.load_contract(self.root)

    def test_named_schema_verification_checks_name_offset_and_each_getter(self):
        name='C_BasePlayerPawn.m_pObserverServices'
        field=self.data['schema'][name]
        base=0x180000000
        record=struct.pack('<QQI',base+0x100,0,int(field['offset'],16))
        blocks={int(field['record_rva'],16):record,0x100:b'm_pObserverServices\0'}
        blocks.update({int(g['rva'],16):bytes.fromhex(g['bytes']) for g in field['getters']})
        image=SimpleNamespace(base=base,read=lambda rva,size:blocks[rva][:size])
        self.assertEqual(generate.verify_named_field(image,name,field),{'offset':0xe98,'getters':2})
        for address in list(blocks):
            old=blocks[address]
            blocks[address]=bytes(len(old))
            with self.subTest(address=address), self.assertRaises((generate.ContractError,KeyError)):
                generate.verify_named_field(image,name,field)
            blocks[address]=old


if __name__ == '__main__':
    unittest.main()
