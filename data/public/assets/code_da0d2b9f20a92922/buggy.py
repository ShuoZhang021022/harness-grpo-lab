def solve(x):
    v = x
    v = v * 3
    v = (v * v) % 101
    v = 2 * v + 1
    v = v // 2
    return v
