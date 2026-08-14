for i in range(60):
    print(f"shard-{i:03d},node-{i // 10}.example.com,{7000 + i},{i % 4 + 1}")
