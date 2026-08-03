from load_tests.http_load import LoadSummary


def test_load_summary_reports_percentiles_and_error_rate():
    summary = LoadSummary(
        total_requests=4,
        successful_requests=3,
        failed_requests=1,
        elapsed_seconds=2.0,
        latencies_ms=(10.0, 20.0, 30.0),
    )

    assert summary.error_rate == 0.25
    assert summary.throughput_per_second == 2.0
    assert summary.percentile_ms(50) == 20.0
    assert summary.percentile_ms(95) == 30.0
