"""Example script: plot energy consumption by sector for EU27."""

import matplotlib.pyplot as plt

from zen_creator.industry_heat_eu.plotting import plot_energy_consumption_by_sector

if __name__ == "__main__":
    plot_energy_consumption_by_sector("EU27", year=2023)
    plt.savefig("outputs/plots/EU27_energy_consumption_by_sector_2023.png", bbox_inches="tight")
    print("Saved plot to outputs/plots/EU27_energy_consumption_by_sector_2023.png")
