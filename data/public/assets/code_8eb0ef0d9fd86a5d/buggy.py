def solve(x):
    v = x
    v = v % 37
    v = v + 7
    v = abs(v)
    v = (v + 5) // 3
    return v
