"""Test riêng cho cải tiến tự thêm: không khẳng định operational khi tool đã lỗi."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from agent import run_agent
from status_tools import StatusTools
from test_lab import FakeProvider, tool_call, final


class ErrorGuardrailTests(unittest.TestCase):
    def test_operational_claim_after_tool_error_gets_revised(self):
        fake = FakeProvider([
            tool_call('1', 'get_status', '{"provider":"cloudflare"}'),
            final('Cloudflare đang hoạt động bình thường (operational).'),
            final('Cloudflare: không xác định được trạng thái do lỗi timeout khi gọi tool.'),
        ])
        result = run_agent('Cloudflare có sự cố không?', fake,
                            StatusTools(fail=True), max_steps=4)
        self.assertEqual(result['status'], 'completed')
        self.assertTrue(any(x['event'] == 'validation_error_ignored' for x in result['trace']))
        self.assertIn('không xác định', result['answer'])

    def test_operational_claim_at_budget_limit_is_not_completed(self):
        fake = FakeProvider([
            tool_call('1', 'get_status', '{"provider":"cloudflare"}'),
            final('Cloudflare đang hoạt động bình thường.'),
        ])
        result = run_agent('x', fake, StatusTools(fail=True), max_steps=2)
        self.assertEqual(result['status'], 'max_steps')

    def test_error_without_operational_claim_is_not_flagged(self):
        fake = FakeProvider([
            tool_call('1', 'get_status', '{"provider":"cloudflare"}'),
            final('Không xác định được trạng thái Cloudflare do lỗi timeout.'),
        ])
        result = run_agent('x', fake, StatusTools(fail=True), max_steps=4)
        self.assertEqual(result['status'], 'completed')
        self.assertFalse(any(x['event'] == 'validation_error_ignored' for x in result['trace']))


class AlwaysRateLimitedTools:
    schemas = []
    def execute(self, name, args):
        return {'ok': False, 'error': 'RATE_LIMITED', 'http_status': 429, 'retriable': True}


class RetryCapTests(unittest.TestCase):
    def test_blocked_retries_do_not_count_as_tool_events(self):
        """Model tiếp tục gọi lại cùng tool sau khi ngân sách retry (3) đã hết."""
        calls = [tool_call(str(i), 'get_vercel_status', '{}') for i in range(1, 5)]
        calls.append(final('Vercel: không xác định được do rate limit kéo dài.'))
        fake = FakeProvider(calls)
        result = run_agent('x', fake, AlwaysRateLimitedTools(), max_steps=8)
        self.assertEqual(result['status'], 'completed')
        tool_events = [t for t in result['trace'] if t['event'] == 'tool' and t['name'] == 'get_vercel_status']
        blocked_events = [t for t in result['trace'] if t['event'] == 'retry_blocked']
        self.assertEqual(len(tool_events), 3, 'mechanical_checks chỉ nên thấy tối đa 3 lần gọi thật')
        self.assertEqual(len(blocked_events), 1, 'lần gọi thứ 2 của model bị chặn hoàn toàn (hết ngân sách)')


if __name__ == '__main__':
    unittest.main()
