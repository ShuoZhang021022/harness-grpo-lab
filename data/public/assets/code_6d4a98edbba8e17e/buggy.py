def solve(x):
    v = x
    v = (v + 5) // 3
    v = (v * v) % 101
    v = abs(v)
    v = 2 * v + 1
    return v
