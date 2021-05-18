## Novelty score for the reaction outcome.
The novelty score is calculated on the processing of the reaction mixture spectrum and is based on the information gain from the spectra (i.e. identified material peaks) and novelty with respect to previously measured spectra of the same reaction mixture.

### Information score.
Approximation of the total information in a given spectrum, based on peaks analysis.
```math
I_{score} = \sum_{i=1}^{r} \left( Size_r \times \frac{1}{\log(|area_r - \overline{area}|)} \right) \times r
```

1. Preprocess spectrum, align with known reference (preferably).
2. Find all potential peak regions ($`r`$), with size of $`Size_r`$ points.
3. Calculate area of all regions ($`area`$).
4. Calculate harmonic mean of all areas ($`\overline{area}`$).
5. Calculate information score for the spectrum using the equation.

**Notes**
- Insensitive to spectrum phasing.
- Will favour spectra with large amount of equal sized peaks.
- Harmonic mean is used to favour smaller peaks and reduce the weight of large spikes and false positives (i.e. noise identified as material peaks).

### Novelty coefficient.
Approximation of the information gain from a single spectrum compared to the previously obtained data.
```math
N_{coef}^{i} = \frac{\vert\text{F}^i\setminus\text{P}\vert}{\vert\text{F}^i\vert} + \frac{1}{\vert\text{P}\vert}, \text{where P} = \bigcup_{j=1}^{k\neq{i}}\text{F}^j
```

1. Always align spectrum with known reference (hence reduce the chance of shifted peaks to be interpreted as novel).
2. Generate set of all points in $`i^{th}`$ spectrum with potential peak regions ($`\text{F}^i`$).
3. Generate set of all points with potential peak regions in all but $`i^{th}`$ ($`k`$) spectra ($`\text{P}`$).
4. Find the set difference for $`i^{th}`$ spectrum and calculate the novelty coefficient by the equation above.

**Notes**
- Insensitive to peak height, but to peak width.
- Very sensitive to spectrum referencing, as light peaks shifts with result in number of "novel" points.
- "$`1/\vert\text{P}\vert`$" is added to increase novelty coefficient even if no new points were found in the current spectrum. It is therefore reduced with increasing number of previous data.

### Final score.
Final score is calculated by multiplication of the Information score ($`I_{score}`$) and Novelty coefficient ($`N_{coef}`$).
