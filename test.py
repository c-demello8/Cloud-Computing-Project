import numpy as np
import matplotlib.pyplot as plt

print("Hello Container !!! ")

x = np.linspace(0,100100)
y = x**2

plt.plot(x,y,label="$y=x^2$")
plt.legend()
plt.savefig("test.png")

print("Bye bYE")


