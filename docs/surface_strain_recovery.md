# Surface strain recovery

Surface strain recovery is the lineage readout attached to a targeted surface
swab. The swab instrument still owns collection efficiency, noise, quality
control, and the recovered abundance. This channel only partitions that
already-recovered abundance across the strain composition held by the existing
PR-4 surface reservoir.

## Conservation contract

For every configured sample:

```
sum(reported lineage abundance) + unresolved abundance = sampled abundance
```

Failed Bernoulli recovery, unreportable genotypes, and lineages below the
reporting floor all become unresolved abundance. They are never silently
dropped or reassigned to another genotype. Reported calls are sorted by
decreasing abundance and then genotype; fractions are descriptive and do not
renormalize the abundances.

The reservoir composition is the same composition used by transmission. Its
age is measured from the last positive surface deposit, and persistence reuses
the transmission core's existing factor:

```
persistence = (1 - SURFACE_DECAY_RATE) ** epochs_since_deposition
```

There is no second incubation, decay, or Ct/LOD model in this channel.

## Parameter anchors

| Parameter | Anchor | Role |
| --- | --- | --- |
| Surface decay factor | Pre-existing transmission-core parameter | Ages the reservoir and attenuates recovery |
| Swab collection efficiency | Pre-existing targeted-surface-swab parameter | Produces the sampled abundance |
| Recovery probabilities by surface type | No literature anchor | Operator dials intended to be swept |
| Reporting floors | No literature anchor | Operator dials intended to be swept |

The defaults are not chosen to flatter shipboard surveillance. They provide a
spread across the existing surface taxonomy so sensitivity and failure modes
remain visible in sweeps.
