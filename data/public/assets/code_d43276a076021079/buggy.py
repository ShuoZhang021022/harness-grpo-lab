def solve(x):
    v = x
    v = (v * v) % 101
    v = v * 3
    v = v // 2
    v = v % 37
    return v
