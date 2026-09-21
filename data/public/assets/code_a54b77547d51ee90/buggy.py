def solve(x):
    v = x
    v = v % 37
    v = v % 37
    v = v * 3
    v = (v + 5) // 3
    return v
