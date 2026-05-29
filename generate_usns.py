import pandas as pd

usns=[]

for i in range(1,101):
    usns.append(f"01fe22bme{i:03}")

df=pd.DataFrame({"USN":usns})

df.to_csv("usns.csv",index=False)

print("Done")