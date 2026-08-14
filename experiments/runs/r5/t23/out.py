for i in range(60):
    print("shard-%03d,node-%d.example.com,%d,%d" % (i, i // 10, 7000 + i, i % 4 + 1))
