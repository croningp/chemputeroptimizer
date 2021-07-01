## Novelty score for the reaction outcome.
The novelty score is calculated on the processing of the reaction mixture spectrum and is based on the information gain from the spectra (i.e. identified material peaks) and novelty with respect to previously measured spectra of the same reaction mixture.

### Region score.

Score of the individual spectrum region, balanced between it's size and total area.

```math
Rs_i = Size_i \times \frac{1}{\log(|area_i - \overline{area}|)}
```
Where $`Size_i`$ is the size of the i<sup>th</sup> region.

1. Preprocess spectrum, align with known reference (preferably).
2. Find all potential peak regions.
3. Calculate areas for each region ($`area_i`$).
4. Calculate harmonic mean of all areas ($`\overline{area}`$).

**Notes**
- If one of the region's $`area_i`$ is equal to $`\overline{area}`$, then it's score is equal to its size.
- Harmonic mean is used to favour smaller peaks and reduce the weight of large spikes and false positives (i.e. noise identified as material peaks).

### Information score
Approximation of the total information in a given spectrum, based on peaks analysis.
```math
Is = \sum_{i=1}^{r} \left(Rs_i\right) \times r
```

**Notes**
- Insensitive to spectrum phasing.
- Will favour spectra with large amount of equal sized peaks.


### Novelty coefficient.
Approximation of the information gain from a single spectrum compared to the previously obtained data.
```math
Nc_{i} = \frac{\vert\text{F}_i\setminus\text{P}\vert}{\vert\text{F}_i\vert} + \frac{1}{\vert\text{P}\vert}, \text{where P} = \bigcup_{j=1}^{k\neq{i}}\text{F}_j
```

1. Always align spectrum with known reference (hence reduce the chance of shifted peaks to be interpreted as novel).
2. Generate set of all points in i<sup>th</sup> spectrum with potential peak regions ($`\text{F}_i`$).
3. Generate set of all points with potential peak regions in all but i<sup>th</sup> ($`k`$) spectra ($`\text{P}`$).
4. Find the set difference for i<sup>th</sup> spectrum and calculate the novelty coefficient by the equation above.

**Notes**
- Insensitive to peak height, but to peak width.
- Very sensitive to spectrum referencing, as light peaks shifts with result in number of "novel" points.
- "$`1/\vert\text{P}\vert`$" is added to increase novelty coefficient even if no new points were found in the current spectrum. It is therefore reduced with increasing number of previous data.

### Final score.
Final score for the spectrum is calculated by multiplication of the Information score ($`Is`$) and Novelty coefficient ($`Nc`$).
