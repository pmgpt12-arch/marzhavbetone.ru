#!/usr/bin/env python3
import copy
import importlib.util
import json
import subprocess
import unittest
from unittest import mock
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("artifact_registry", Path(__file__).with_name("build_artifact_registry.py"))
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(MODULE)
BASE = json.loads((ROOT / "products-storage/ARTIFACT-REGISTRY.json").read_text(encoding="utf-8"))


class RegistryShapeTests(unittest.TestCase):
    def test_seed_is_valid(self):
        MODULE.validate_shape(copy.deepcopy(BASE))

    def test_duplicate_registry_id_fails(self):
        data = copy.deepcopy(BASE)
        data["artifacts"].append(copy.deepcopy(data["artifacts"][0]))
        with self.assertRaises(MODULE.RegistryError):
            MODULE.validate_shape(data)

    def test_missing_target_fails(self):
        data = copy.deepcopy(BASE)
        data["product_sources"] = [row for row in data["product_sources"] if row.get("target_sku") != "T3"]
        with self.assertRaises(MODULE.RegistryError):
            MODULE.validate_shape(data)

    def test_report_cannot_be_canonical(self):
        data = copy.deepcopy(BASE)
        data["artifacts"][2]["role"] = "canonical_master"
        with self.assertRaises(MODULE.RegistryError):
            MODULE.validate_shape(data)

    def test_non_nominated_report_is_blocked(self):
        data = copy.deepcopy(BASE)
        data["artifacts"][2]["release_status"] = "OPEN"
        with self.assertRaises(MODULE.RegistryError):
            MODULE.validate_shape(data)

    def test_unknown_role_fails(self):
        data = copy.deepcopy(BASE)
        data["artifacts"][0]["role"] = "accepted_somewhere_else"
        with self.assertRaises(MODULE.RegistryError):
            MODULE.validate_shape(data)

    def test_coverage_drift_fails(self):
        data = copy.deepcopy(BASE)
        data["coverage"]["file_sha256_records"]["registered"] = 217
        with self.assertRaises(MODULE.RegistryError):
            MODULE.validate_shape(data)

    def test_runtime_root_count_fails_even_when_coverage_is_reconciled(self):
        data = copy.deepcopy(BASE)
        data["product_sources"] = [row for row in data["product_sources"] if row.get("runtime_sku") != "test1"]
        root_files = sum(int(row.get("file_count", 0)) for row in data["product_sources"])
        data["coverage"]["runtime_roots"] = {"registered": len(data["product_sources"]), "expected": 19}
        data["coverage"]["root_files"] = root_files
        data["coverage"]["file_sha256_records"]["expected"] = root_files
        data["coverage"]["file_sha256_records"]["percent"] = round(
            100 * len(data["artifacts"]) / root_files, 2
        )
        with self.assertRaises(MODULE.RegistryError):
            MODULE.validate_shape(data)

    def test_missing_report_object_fails(self):
        data = {
            "product_sources": [],
            "artifacts": [copy.deepcopy(BASE["artifacts"][2])],
        }
        missing = subprocess.CalledProcessError(128, ["git", "rev-parse"])
        with mock.patch.object(MODULE, "git", side_effect=missing):
            with self.assertRaises(MODULE.RegistryError):
                MODULE.reconcile(data, ROOT, True)

    def test_checkout_matches_seed(self):
        try:
            subprocess.check_call(["git", "-C", str(ROOT), "rev-parse", "--git-dir"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except subprocess.CalledProcessError:
            self.skipTest("not running in a git checkout")
        self.assertFalse(MODULE.reconcile(copy.deepcopy(BASE), ROOT, True))


class RegistryChangeHistoryTests(unittest.TestCase):
    def history(self):
        return copy.deepcopy(BASE)

    def reseal(self, data):
        previous = None
        for r in data['change_history']['records']:
            r['previous_record_sha256'] = previous
            for g in r['gates']:
                g['contract_sha256'] = MODULE.stable_digest(g['contract'])
                g['environment_fingerprint'] = MODULE.stable_digest(g['environment'])
                g['dependency_fingerprint'] = MODULE.stable_digest(g['dependencies'])
                g['fingerprint'] = MODULE.gate_fingerprint(r, g)
            r['record_sha256'] = MODULE.change_record_digest(r)
            previous = r['record_sha256']
        data['change_history']['record_count'] = len(data['change_history']['records'])
        data['change_history']['head_record_sha256'] = previous
        return data

    def request(self, data, index=-1, gate_index=0):
        r = data['change_history']['records'][index]
        g = r['gates'][gate_index]
        return {'record_id': r['record_id'], 'gate_id': g['gate_id'], 'actual_input_path': str(ROOT/r['output']['archive_path']), **{k:g[k] for k in ('contract_sha256','environment_fingerprint','dependency_fingerprint')}}

    def test_history_current_records_valid(self):
        MODULE.validate_change_history(self.history())
        MODULE.verify_history_files(BASE, ROOT)

    def word_index(self, data):
        rows=data['change_history']['records']
        ids=[i for i,r in enumerate(rows) if any(g.get('job_id')=='p2-instruction-style-word-20261013-v1' for g in r['gates'])]
        self.assertEqual(len(ids),1)
        return ids[0]

    def numeric_index(self, data):
        ids=[i for i,r in enumerate(data['change_history']['records']) if r['record_id']=='P1-395-NUMERIC-ORDINARY-365-20261013']
        self.assertEqual(len(ids),1)
        return ids[0]

    def test_exact_word_pass_reused_without_new_job(self):
        result = MODULE.plan_checkpoint_reuse(BASE, self.request(BASE,self.word_index(BASE)), ROOT)
        self.assertEqual(result['decision'], 'REUSE_VERIFIED_RESULT')
        self.assertTrue(result['do_not_launch_duplicate'])
        self.assertEqual(result['job_id'], 'p2-instruction-style-word-20261013-v1')
        self.assertEqual(result['release_status'], 'BLOCKED')

    def test_known_excel_failure_is_not_retried(self):
        result = MODULE.plan_checkpoint_reuse(BASE, self.request(BASE,0), ROOT)
        self.assertEqual(result['decision'], 'BLOCK_KNOWN_FAILURE')
        self.assertTrue(result['do_not_launch_duplicate'])

    def test_changed_input_requires_delta_not_reuse(self):
        request = self.request(BASE)
        request['actual_input_path'] = self.request(BASE,0)['actual_input_path']
        result = MODULE.plan_checkpoint_reuse(BASE, request, ROOT)
        self.assertEqual(result['decision'], 'DELTA_RECHECK_REQUIRED')
        self.assertIn('subject_sha256', result['changed_dimensions'])

    def test_changed_contract_requires_delta(self):
        request = self.request(BASE); request['contract_sha256']='0'*64
        self.assertEqual(MODULE.plan_checkpoint_reuse(BASE,request,ROOT)['decision'],'DELTA_RECHECK_REQUIRED')

    def test_changed_runtime_requires_delta(self):
        request = self.request(BASE); request['environment_fingerprint']='0'*64
        self.assertEqual(MODULE.plan_checkpoint_reuse(BASE,request,ROOT)['decision'],'DELTA_RECHECK_REQUIRED')

    def test_changed_dependencies_require_delta(self):
        request = self.request(BASE); request['dependency_fingerprint']='0'*64
        self.assertEqual(MODULE.plan_checkpoint_reuse(BASE,request,ROOT)['decision'],'DELTA_RECHECK_REQUIRED')

    def test_unknown_current_contract_blocks(self):
        request=self.request(BASE);request.pop('contract_sha256')
        with self.assertRaises(MODULE.RegistryError):MODULE.plan_checkpoint_reuse(BASE,request,ROOT)

    def test_record_digest_tampering_fails(self):
        data=self.history();data['change_history']['records'][-1]['origin']['reason']='unrecorded edit'
        with self.assertRaises(MODULE.RegistryError):MODULE.validate_change_history(data)

    def test_deleted_history_record_fails(self):
        data=self.history();data['change_history']['records'].pop(0)
        with self.assertRaises(MODULE.RegistryError):MODULE.validate_change_history(data)

    def test_broken_history_link_fails(self):
        data=self.history();data['change_history']['records'][-1]['previous_record_sha256']='0'*64
        with self.assertRaises(MODULE.RegistryError):MODULE.validate_change_history(data)

    def test_duplicate_record_id_fails_after_reseal(self):
        data=self.history();data['change_history']['records'][-1]['record_id']=data['change_history']['records'][0]['record_id'];self.reseal(data)
        with self.assertRaises(MODULE.RegistryError):MODULE.validate_change_history(data)

    def test_gate_cannot_refer_to_another_subject(self):
        data=self.history();data['change_history']['records'][-1]['gates'][0]['subject_sha256']='0'*64;self.reseal(data)
        with self.assertRaises(MODULE.RegistryError):MODULE.validate_change_history(data)

    def test_unbounded_pass_rejected(self):
        data=self.history();data['change_history']['records'][-1]['gates'][0]['accepted_scope_only']=False;self.reseal(data)
        with self.assertRaises(MODULE.RegistryError):MODULE.validate_change_history(data)

    def test_false_release_pass_rejected(self):
        data=self.history();data['change_history']['records'][-1]['release_status']='PASS';self.reseal(data)
        with self.assertRaises(MODULE.RegistryError):MODULE.validate_change_history(data)

    def test_false_product_pass_rejected(self):
        data=self.history();data['change_history']['records'][-1]['resume']['g1_g8_status']='PASS';self.reseal(data)
        with self.assertRaises(MODULE.RegistryError):MODULE.validate_change_history(data)

    def test_archive_escape_rejected(self):
        data=self.history();data['change_history']['records'][-1]['evidence'][0]['archive_path']='../old.pdf';self.reseal(data)
        with self.assertRaises(MODULE.RegistryError):MODULE.validate_change_history(data)

    def test_missing_archive_blocks_reuse(self):
        data=self.history();data['change_history']['records'][-1]['evidence'][0]['archive_path']='tools/candidates/registry-history-evidence/missing.json';self.reseal(data)
        with self.assertRaises(MODULE.RegistryError):MODULE.plan_checkpoint_reuse(data,self.request(data),ROOT)

    def test_corrupt_archive_digest_blocks_reuse(self):
        data=self.history();data['change_history']['records'][-1]['evidence'][0]['sha256']='0'*64;self.reseal(data)
        with self.assertRaises(MODULE.RegistryError):MODULE.plan_checkpoint_reuse(data,self.request(data),ROOT)

    def test_exact_duplicate_append_is_noop(self):
        data=self.history();before=copy.deepcopy(data);record=copy.deepcopy(data['change_history']['records'][-1])
        self.assertFalse(MODULE.append_change_record(data,record,data['change_history']['head_record_sha256']))
        self.assertEqual(data,before)

    def test_rewrite_historical_id_rejected(self):
        data=self.history();record=copy.deepcopy(data['change_history']['records'][-1]);record['origin']['reason']='different result'
        with self.assertRaises(MODULE.RegistryError):MODULE.append_change_record(data,record,data['change_history']['head_record_sha256'])

    def test_concurrent_history_head_rejected(self):
        data=self.history();record=copy.deepcopy(data['change_history']['records'][-1]);record['record_id']='new-record'
        with self.assertRaises(MODULE.RegistryError):MODULE.append_change_record(data,record,'0'*64)

    def test_same_job_and_fingerprint_cannot_be_recorded_twice(self):
        data=self.history();record=copy.deepcopy(data['change_history']['records'][-1]);record['record_id']='duplicate-execution'
        with self.assertRaises(MODULE.RegistryError):MODULE.append_change_record(data,record,data['change_history']['head_record_sha256'])

    def test_open_print_gate_not_converted_to_pass(self):
        result=MODULE.plan_checkpoint_reuse(BASE,self.request(BASE,2,1),ROOT)
        self.assertEqual(result['decision'],'CHECK_REQUIRED')
        self.assertEqual(result['g1_g8_status'],'NOT_FULLY_ACCEPTED')

    def test_pending_job_requires_wait(self):
        data=self.history();data['change_history']['records'][-1]['gates'][0]['status']='PENDING';self.reseal(data)
        result=MODULE.plan_checkpoint_reuse(data,self.request(data),ROOT)
        self.assertEqual(result['decision'],'WAIT_EXISTING_JOB');self.assertTrue(result['do_not_launch_duplicate'])

    def test_cached_native_pass_cannot_override_raw_fail(self):
        data=self.history();data["change_history"]["records"][0]["gates"][0]["status"]="PASS";self.reseal(data)
        with self.assertRaises(MODULE.RegistryError): MODULE.plan_checkpoint_reuse(data,self.request(data,0),ROOT)

    def test_cached_native_fail_cannot_override_raw_pass(self):
        data=self.history();i=self.word_index(data);data["change_history"]["records"][i]["gates"][0]["status"]="FAIL";self.reseal(data)
        with self.assertRaises(MODULE.RegistryError): MODULE.plan_checkpoint_reuse(data,self.request(data,i),ROOT)

    def test_named_word_checkpoint_survives_appended_numeric_records(self):
        self.assertLess(self.word_index(BASE),len(BASE['change_history']['records'])-1)
        result=MODULE.plan_checkpoint_reuse(BASE,self.request(BASE,self.word_index(BASE)),ROOT)
        self.assertEqual(result['job_id'],'p2-instruction-style-word-20261013-v1')

    def test_numeric_cached_fail_cannot_override_raw_pass(self):
        data=self.history();i=self.numeric_index(data);data['change_history']['records'][i]['gates'][0]['status']='FAIL';self.reseal(data)
        with self.assertRaises(MODULE.RegistryError):MODULE.verify_history_files(data,ROOT)

    def test_numeric_batch_wrong_tag_rejected(self):
        data=self.history();i=self.numeric_index(data);data['change_history']['records'][i]['execution']['tag']='p1n4';self.reseal(data)
        with self.assertRaises(MODULE.RegistryError):MODULE.verify_history_files(data,ROOT)

    def test_numeric_wrong_raw_job_rejected(self):
        data=self.history();i=self.numeric_index(data);data['change_history']['records'][i]['gates'][0]['job_id']='wrong-job';self.reseal(data)
        with self.assertRaises(MODULE.RegistryError):MODULE.verify_history_files(data,ROOT)

    def test_baseline_inventory_not_replaced(self):
        self.assertEqual(BASE['file_inventory']['files'],218)
        self.assertEqual(BASE['file_inventory']['sha256'],'f9ea9acb1c39826599787ebdc9372765863a48b8f812eb14c41a39d12627da5f')
        self.assertEqual(len(BASE['artifacts']),4)


if __name__ == "__main__":
    unittest.main()
