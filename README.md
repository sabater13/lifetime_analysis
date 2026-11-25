# 2x2 Lifetime Analysis

Set of scripts to plot the electron lifetime from flow charge hdf5 files. This is using the track drift time method.

Need to have 2x2 nearline installed to run any of the fits.

## Drift Time Electron Lifetime Fit
Segments with non-zero track length are selected and their dQ/dx is binned as a function of drift time. A langau fit is applied to this histogram distrubution to extracat the MPV of each bin. This MPVs are then plotted in the same 19 drift time bins. An exponential fit is then applied $$f(t) = Ae^{-t/\tau}$$ where
- $f(t)$: MPV of the histogram-convolution
- $t$: electron drift time ($\mu$s)
- $\tau$: electron lifetime ($\mu$s)

10 bins out of 19 need to be filled in the new version (in [Josh's arcube_nearline](https://github.com/joshuabarrow221/arcube_nearline/tree/dev/purity-overlay)).