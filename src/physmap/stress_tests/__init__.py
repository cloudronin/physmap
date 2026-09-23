"""Controlled stress tests of the causal path.

A stress test here is a deliberately constructed situation with a known answer, used to show
what a check can and cannot see. It is a development demonstration, not an evaluation: no
performance metric is computed or implied. Each one reproduces from the checkout with one
command and is drift-checked against a committed bank, the same way `physmap benchmark run`
is -- and each is kept apart from that benchmark, which measures closure validity and
observability, not materiality.
"""
