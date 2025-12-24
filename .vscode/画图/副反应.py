import matplotlib.pyplot as plt
import numpy as np
from pymatgen.core.periodic_table import Element
import matplotlib as mpl

# Set font to avoid Chinese characters
plt.rcParams['font.family'] = 'Arial'

# Reaction data: element symbol and corresponding reaction energy
reaction_data = {
    'Ce': -0.513631544, 'Cr': 0.081794104, 'Fe': 0.131372233, 'Gd': 0.179138196,
    'Nd': 0.081123676, 'Sc': 0.126638448, 'Sn': 0.151688393, 'Bi': 0.093997289,
    'Sb': 0.127317151, 'Lu': 0.180714804, 'Al': -0.326518634, 'Mg': 0.337306323,
    'Ba': 1.181048323, 'Ca': 0.60184366, 'Co': 0.197965757, 'Cu': 0.13432166,
    'Mn': 0.250449823, 'Ni': 0.168802997, 'Sr': 0.696606549, 'Zn': 0.142130078,
    'Na': 0.323463059, 'Li': 0.242473617,'Y': 0.070590909,'In': 0.163658103


}

# Define element positions based on the standard periodic table layout
# Using 0-based indexing: (row, column)
element_positions = {
    # Period 1
    'H': (0, 0), 'He': (0, 17),
    
    # Period 2
    'Li': (1, 0), 'Be': (1, 1), 'B': (1, 12), 'C': (1, 13), 'N': (1, 14), 
    'O': (1, 15), 'F': (1, 16), 'Ne': (1, 17),
    
    # Period 3
    'Na': (2, 0), 'Mg': (2, 1), 'Al': (2, 12), 'Si': (2, 13), 'P': (2, 14), 
    'S': (2, 15), 'Cl': (2, 16), 'Ar': (2, 17),
    
    # Period 4
    'K': (3, 0), 'Ca': (3, 1), 'Sc': (3, 2), 'Ti': (3, 3), 'V': (3, 4), 
    'Cr': (3, 5), 'Mn': (3, 6), 'Fe': (3, 7), 'Co': (3, 8), 'Ni': (3, 9), 
    'Cu': (3, 10), 'Zn': (3, 11), 'Ga': (3, 12), 'Ge': (3, 13), 'As': (3, 14), 
    'Se': (3, 15), 'Br': (3, 16), 'Kr': (3, 17),
    
    # Period 5
    'Rb': (4, 0), 'Sr': (4, 1), 'Y': (4, 2), 'Zr': (4, 3), 'Nb': (4, 4), 
    'Mo': (4, 5), 'Tc': (4, 6), 'Ru': (4, 7), 'Rh': (4, 8), 'Pd': (4, 9), 
    'Ag': (4, 10), 'Cd': (4, 11), 'In': (4, 12), 'Sn': (4, 13), 'Sb': (4, 14), 
    'Te': (4, 15), 'I': (4, 16), 'Xe': (4, 17),
    
    # Period 6
    'Cs': (5, 0), 'Ba': (5, 1), 
    # Lanthanides placeholder
    'Lu': (5, 2), 'Hf': (5, 3), 'Ta': (5, 4), 'W': (5, 5), 'Re': (5, 6), 
    'Os': (5, 7), 'Ir': (5, 8), 'Pt': (5, 9), 'Au': (5, 10), 'Hg': (5, 11), 
    'Tl': (5, 12), 'Pb': (5, 13), 'Bi': (5, 14), 'Po': (5, 15), 'At': (5, 16), 
    'Rn': (5, 17),
    
    # Period 7
    'Fr': (6, 0), 'Ra': (6, 1),
    # Actinides placeholder
    'Lr': (6, 2), 'Rf': (6, 3), 'Db': (6, 4), 'Sg': (6, 5), 'Bh': (6, 6), 
    'Hs': (6, 7), 'Mt': (6, 8), 'Ds': (6, 9), 'Rg': (6, 10), 'Cn': (6, 11), 
    'Nh': (6, 12), 'Fl': (6, 13), 'Mc': (6, 14), 'Lv': (6, 15), 'Ts': (6, 16), 
    'Og': (6, 17),
}

# Lanthanides (row 8, columns 3-17)
lanthanides = {
    'La': (7, 3), 'Ce': (7, 4), 'Pr': (7, 5), 'Nd': (7, 6), 'Pm': (7, 7),
    'Sm': (7, 8), 'Eu': (7, 9), 'Gd': (7, 10), 'Tb': (7, 11), 'Dy': (7, 12),
    'Ho': (7, 13), 'Er': (7, 14), 'Tm': (7, 15), 'Yb': (7, 16), 'Lu': (7, 17)
}

# Actinides (row 9, columns 3-17)
actinides = {
    'Ac': (8, 3), 'Th': (8, 4), 'Pa': (8, 5), 'U': (8, 6), 'Np': (8, 7),
    'Pu': (8, 8), 'Am': (8, 9), 'Cm': (8, 10), 'Bk': (8, 11), 'Cf': (8, 12),
    'Es': (8, 13), 'Fm': (8, 14), 'Md': (8, 15), 'No': (8, 16), 'Lr': (8, 17)
}

# Combine all positions
all_element_positions = {**element_positions, **lanthanides, **actinides}

# Create the plot with proper dimensions
fig, ax = plt.subplots(figsize=(20, 12))

# Create a custom colormap from red (lowest) to blue (highest)
cmap = mpl.colors.LinearSegmentedColormap.from_list('reaction_energy', ['red', 'white', 'blue'])

# Find min and max energy for normalization
energies = list(reaction_data.values())
#vmin, vmax = min(energies), max(energies)
vmin, vmax = -1,1
# Normalize the colormap
norm = mpl.colors.Normalize(vmin=vmin, vmax=vmax)

# Plot all elements in the main table
for element_symbol in all_element_positions.keys():
    row, col = all_element_positions[element_symbol]
    
    # Determine color based on whether we have data
    if element_symbol in reaction_data:
        energy = reaction_data[element_symbol]
        facecolor = cmap(norm(energy))
        has_data = True
    else:
        facecolor = 'lightgray'
        has_data = False
    
    # Create rectangle for the element cell
    rect = plt.Rectangle((col, -row), 1, 1, 
                       facecolor=facecolor,
                       edgecolor='black',
                       linewidth=1.5,
                       alpha=0.8)
    ax.add_patch(rect)
    
    # Add element symbol (larger font for elements with data)
    if has_data:
        ax.text(col + 0.5, -row + 0.7, element_symbol, 
               ha='center', va='center', fontsize=14, fontweight='bold')
        # Add energy value
        ax.text(col + 0.5, -row + 0.3, f'{reaction_data[element_symbol]:.3f}', 
               ha='center', va='center', fontsize=9, fontweight='bold')
    else:
        ax.text(col + 0.5, -row + 0.5, element_symbol, 
               ha='center', va='center', fontsize=10, alpha=0.7)
    
    # Add atomic number for all elements
    try:
        element_obj = Element(element_symbol)
        atomic_number = element_obj.Z
        ax.text(col + 0.1, -row + 0.9, str(atomic_number), 
               ha='left', va='top', fontsize=7, alpha=0.7)
    except:
        pass

# Add connecting indicators for lanthanides and actinides
# Indicator from Ba to lanthanides
ax.plot([1.5, 3.5], [-5.5, -7.5], 'k--', alpha=0.3, linewidth=1)
# Indicator from Lu to actinides
ax.plot([1.5, 3.5], [-5.5, -8.5], 'k--', alpha=0.3, linewidth=1)

# Set axis limits
ax.set_xlim(-1, 18)
ax.set_ylim(-10, 2)
ax.set_aspect('equal')

# Remove axes ticks and labels
ax.set_xticks([])
ax.set_yticks([])

# Add group numbers (1-18)
for col in range(18):
    ax.text(col + 0.5, 1.2, str(col + 1), 
           ha='center', va='center', fontsize=12, fontweight='bold')

# Add period numbers (1-7)
for row in range(7):
    ax.text(-0.5, -row + 0.5, str(row + 1), 
           ha='center', va='center', fontsize=12, fontweight='bold')

# Add labels for lanthanides and actinides
ax.text(-0.8, -7.5, 'Lanthanides', ha='center', va='center', 
        fontsize=11, fontweight='bold', rotation=90)
ax.text(-0.8, -8.5, 'Actinides', ha='center', va='center', 
        fontsize=11, fontweight='bold', rotation=90)

# Add title in the style of the reference image
ax.set_title('Reaction Energy Distribution on Periodic Table', 
            fontsize=20, fontweight='bold', pad=30)

# Add subtitle
ax.text(0.5, 1.8, 'Color represents reaction energy (eV/atom)', 
        ha='left', va='center', fontsize=14, style='italic')

# Add colorbar
cbar = plt.colorbar(mpl.cm.ScalarMappable(norm=norm, cmap=cmap), 
                   ax=ax, shrink=0.6, pad=0.02)
cbar.set_label('Reaction Energy (eV/atom)', fontsize=12)
cbar.ax.tick_params(labelsize=10)

# Add legend
legend_elements = [
    plt.Rectangle((0, 0), 1, 1, facecolor='lightgray', edgecolor='black', label='No data'),
    plt.Rectangle((0, 0), 1, 1, facecolor='red', edgecolor='black', label='Low energy (negative)'),
    plt.Rectangle((0, 0), 1, 1, facecolor='blue', edgecolor='black', label='High energy (positive)')
]
ax.legend(handles=legend_elements, loc='upper right', bbox_to_anchor=(1.15, 1), 
          fontsize=10, framealpha=0.9)

# Add informational text similar to reference image
info_text = """Reaction Energy Scale:
Red: Low (negative) energy
Blue: High (positive) energy
Gray: No reaction data available"""
ax.text(16, -9, info_text, fontsize=9, 
        bbox=dict(boxstyle="round,pad=0.5", facecolor='lightyellow', alpha=0.8))

plt.tight_layout()

# Save the plot
plt.savefig('standard_periodic_table_reaction_energy.png', dpi=300, 
            bbox_inches='tight', facecolor='white')
plt.savefig('standard_periodic_table_reaction_energy.pdf', 
            bbox_inches='tight', facecolor='white')

plt.show()

# Print statistics
print(f"Standard Periodic Table Layout Created")
print(f"Elements with reaction energy data: {len(reaction_data)}")
print(f"Total elements displayed: {len(all_element_positions)}")
print(f"Reaction energy range: {vmin:.3f} to {vmax:.3f} eV/atom")

