def solve(x):
    v = x
    v = -v
    v = (v + 5) // 3
    v = v // 2
    v = (v * v) % 101
    return v
