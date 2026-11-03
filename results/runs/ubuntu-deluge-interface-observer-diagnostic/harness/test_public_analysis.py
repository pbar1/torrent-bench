import unittest

from analyze_ubuntu import audit_samples, distribution, summarize_client, wilson


class PublicAnalysisTests(unittest.TestCase):
    def test_inclusive_quartiles_and_all_observations(self):
        result = distribution([1, 2, 3, 4, 5, 100])
        self.assertEqual(result['n'], 6)
        self.assertEqual((result['q1'], result['median'], result['q3']), (2.25, 3.5, 4.75))
        self.assertEqual((result['min'], result['max']), (1, 100))

    def test_empty_and_singleton(self):
        self.assertEqual(distribution([])['median'], None)
        self.assertEqual(distribution([3])['q3'], 3)

    def test_wilson_does_not_imply_certainty_after_six_successes(self):
        low, high = wilson(6, 6)
        self.assertAlmostEqual(low, 0.6096657121)
        self.assertAlmostEqual(high, 1)
        self.assertAlmostEqual(wilson(0, 6)[1], 1 - low)

    def test_failure_is_retained_and_penalized_without_fake_throughput(self):
        def trial(status, elapsed, speed):
            fields = ('cpu_s', 'network_rx', 'network_tx', 'peak_rss_mib',
                      'peak_anon_mib', 'peak_memory_mib', 'peak_working_mib')
            return {'client': 'example', 'status': status, 'elapsed_s': elapsed,
                    'mib_s': speed, 'details': {},
                    'metrics': {'client': dict.fromkeys(fields, 1)}}
        result = summarize_client([trial('ok', 30, 10), trial('timeout', 901, None),
                                   trial('error', 2, None)], 900)
        self.assertEqual(result['n'], 3)
        self.assertEqual(result['completed'], 1)
        self.assertEqual(result['deadline_penalized_mean_s'], 610)
        self.assertEqual(result['mib_s']['n'], 1)
        self.assertEqual(result['mib_s']['median'], 10)
        self.assertEqual(result['cpu_s']['n'], 3)
        self.assertIsNone(result['discovery']['max_observed_ipv6_peers'])

    def test_audit_rejects_reported_peak_that_disagrees_with_raw_samples(self):
        fields = ('memory_mib', 'working_mib', 'anon_mib', 'file_mib', 'rss_mib')
        deltas = ('cpu_s', 'throttled_s', 'network_rx', 'network_tx', 'io_read', 'io_write')
        tag = {'client': 'example', 'repeat': 0}
        samples = [{'trial': tag, 'time': time,
                    'client': dict.fromkeys(fields + deltas, value)}
                   for time, value in ((1, 10), (2, 20), (3, 30))]
        recorded = {**dict.fromkeys(('peak_' + f for f in fields), 30),
                    **dict.fromkeys(('median_' + f for f in fields), 20),
                    **dict.fromkeys(deltas, 20)}
        trial = {**tag, 'metrics': {'samples': 3, 'measurement_s': 2, 'client': recorded}}
        self.assertEqual(audit_samples([trial], samples)['example']['max'], 1)
        recorded['peak_anon_mib'] = 19
        with self.assertRaises(AssertionError):
            audit_samples([trial], samples)

    def test_hash_scan_progress_is_not_reported_as_network_startup(self):
        fields = ('cpu_s', 'network_rx', 'network_tx', 'peak_rss_mib',
                  'peak_anon_mib', 'peak_memory_mib', 'peak_working_mib')
        trial = {'client': 'rqbit', 'status': 'ok', 'elapsed_s': 30, 'mib_s': 10,
                 'details': {'first_observed_payload_s': 0.01, 'active_10_90_mib_s': 9999},
                 'metrics': {'client': dict.fromkeys(fields, 1)}}
        result = summarize_client([trial], 900)
        self.assertEqual(result['first_observed_payload_s']['n'], 0)
        self.assertEqual(result['active_10_90_mib_s']['n'], 0)
        self.assertEqual(result['mib_s']['median'], 10)


if __name__ == '__main__':
    unittest.main()
