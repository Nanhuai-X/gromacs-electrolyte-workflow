# Gaussian CPCM mapping audit for RESP2

## Source environment

The RESP2 paper reports Psi4 CPCM water with dielectric constant epsilon=78.39
and Bondi radii for the aqueous ESP calculation. The Gaussian branch uses the
explicit route keyword `SCRF=(CPCM,Solvent=Water)` and the same PW6B95 basis
mapping as the gas branch. Gaussian 16 Rev. A.03 rejects the literal
`aug-cc-pV(D+d)Z` route syntax. For the present H/C/N/O fixtures, where no
second-row tight-d function is used, the audited executable mapping is
`aug-cc-pVDZ`; both source and executable notation are retained in manifests.
This is an explicit implementation limitation, not a silent substitution.

## Mapping

| Aspect | Original reported protocol | Gaussian mapping | Status |
|---|---|---|---|
| dielectric | 78.39 | Gaussian named water solvent (`CPCM,Solvent=Water`) | SOFTWARE_DEFAULT_REQUIRES_AUDIT |
| cavity radii | Bondi radii | Gaussian CPCM default cavity unless an explicit Bondi mapping is proven | NOT_BITWISE_IDENTICAL |
| cavity model | CPCM | CPCM | MODEL_FAMILY_MATCH |
| electrostatic treatment | implicit reaction field | Gaussian CPCM reaction field | MODEL_FAMILY_MATCH |
| QM basis | PW6B95/aug-cc-pV(D+d)Z | PW6B95/aug-cc-pVDZ for H/C/N/O fixtures | IMPLEMENTATION_MAPPING |
| ESP points | Respyte MSK, 1.6-2.0 Ri, 0.2 Ri, 2.4 points/A2 | Native Multiwfn local RESP point generation | IMPLEMENTATION_DIFFERENCE |
| RESP solver | Respyte | Native Multiwfn 3.8_dev | IMPLEMENTATION_DIFFERENCE |

The mapping is therefore named `RESP2_PROTOCOL_REPRODUCTION_WITH_GAUSSIAN`.
It must not be called `BITWISE_OR_SOFTWARE_IDENTICAL_RESP2`. The exact
Gaussian route lines, logs, FCHK hashes, Multiwfn registry, and branch
comparison are the auditable evidence.
