def solve(x):
    v = x
    v = 2 * v + 1
    v = (v + 5) // 3
    v = abs(v)
    v = (v * v) % 101
    return v
