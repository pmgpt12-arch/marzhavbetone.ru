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

    def test_exact_word_pass_reused_without_new_job(self):
        result = MODULE.plan_checkpoint_reuse(BASE, self.request(BASE), ROOT)
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

    def test_baseline_inventory_not_replaced(self):
        self.assertEqual(BASE['file_inventory']['files'],218)
        self.assertEqual(BASE['file_inventory']['sha256'],'f9ea9acb1c39826599787ebdc9372765863a48b8f812eb14c41a39d12627da5f')
        self.assertEqual(len(BASE['artifacts']),4)
