# MTBF Calculator

## Purpose

Estimate MTBF from observed data: operating hours and a failure count, a fleet of units that each ran a
known time, or a list of individual failure times. Every estimate is reported with a confidence interval,
because an MTBF built on a handful of failures is far softer than the single number suggests.

This tool goes from data to an MTBF. To go the other way, combining known component MTBFs into a system
reliability, use the [System Reliability Calculator](../system-reliability/).

## Workflow

- Pick how your data is shaped: total hours plus failures, a fleet of N units run H hours each, or
  individual times to failure.
- Enter suspensions (units that had not failed when you stopped watching) if you have them. Their run time
  is evidence that the design survived that long, and leaving it out biases the estimate low.
- Choose a distribution. Exponential is the default and the only option for aggregate data. Weibull and
  lognormal need individual failure times.
- Set a confidence level and the mission time you care about, then read the reliability at that mission
  time alongside the MTBF.

## Inputs

- Data mode: aggregate, fleet, or individual failure times.
- Total operating hours (aggregate), or unit count and hours per unit (fleet).
- Failure count (aggregate and fleet modes).
- Failure times and suspension times in hours (failure-times mode).
- Distribution: exponential, Weibull, or lognormal.
- Test termination: time-terminated or failure-terminated. Changes the exponential lower bound.
- Confidence level (60% to 99%) and mission time in hours.

## Outputs

- MTBF (exponential) or MTTF (Weibull, lognormal) with two-sided and one-sided confidence bounds.
- Failure rate in failures per hour and in FIT (failures per 10^9 hours).
- Reliability at the mission time, B10 life, and median life.
- Fitted distribution parameters with bounds: theta, or beta and eta, or mu and sigma.
- Reliability and hazard-rate curves, plus a probability plot with median-rank plotting positions.
- Notes on sample size, shape, and censoring that qualify the numbers.

## Methods

- Exponential: MTBF = T / r, with exact chi-squared confidence bounds. The lower bound uses 2r+2 degrees
  of freedom for a time-terminated test and 2r for a failure-terminated one.
- Weibull: maximum likelihood on right-censored data. The shape equation is solved by bisection on the
  profile likelihood, then eta follows in closed form. MTTF = eta * gamma(1 + 1/beta).
- Lognormal: closed-form maximum likelihood for complete data, simplex search on the censored likelihood
  when suspensions are present. MTTF = exp(mu + sigma^2/2).
- Confidence bounds for Weibull and lognormal come from the observed Fisher information (numeric Hessian of
  the log-likelihood), with the delta method applied in log space so intervals stay positive and asymmetric.
- Plotting positions use Benard's median-rank approximation with Johnson adjusted ranks for suspensions.

## Assumptions and Limitations

- Units are identical and failures are independent.
- Hours are operating hours. Calendar time on an idle unit is not operating time.
- Repaired items are assumed restored to their original condition, with no degradation accumulating across
  repairs.
- The exponential model assumes a constant hazard rate: no infant mortality, no wear-out.
- Weibull and lognormal confidence bounds are large-sample approximations. Below roughly 10 failures, treat
  their width as indicative.
- One failure mode at a time. A probability plot with a knee or two slopes means mixed modes that should be
  fitted separately.

## References

- Ebeling, C.E. An Introduction to Reliability and Maintainability Engineering, 3rd ed., Chapters 12 and 15.
- O'Connor, P.D.T. and Kleyner, A. Practical Reliability Engineering, 5th ed., Chapters 3 and 13.
- Abernethy, R.B. The New Weibull Handbook, 5th ed. (median ranks, suspended-item ranking).
- IEC 60300-3-5: Dependability management - Reliability test conditions and statistical test principles.
- MIL-HDBK-781A: Reliability Test Methods, Plans, and Environments (test termination conventions).
