namespace CEOverPressure

open System

[<Struct>]
type internal PressureModelParameters =
    { MetresPerCell: float32
      ReferenceDamage: float32
      ReferenceYieldKg: float32
      YieldExponent: float32
      MinimumYieldKg: float32
      MaximumYieldKg: float32
      MinimumPressureYieldKg: float32
      RangeCoefficientMetres: float32
      MinimumScaledDistance: float32
      CloseRangeLimit: float32
      CloseCubicCoefficient: float32
      CloseOffset: float32
      FarLinearCoefficient: float32
      FarQuadraticCoefficient: float32
      FarCubicCoefficient: float32
      FarOffset: float32
      PressureUnitKPa: float32 }

module internal PressureModel =
    let private power value exponent = Math.Pow(float value, float exponent) |> float32
    let private cubeRoot value = power value (1.0f / 3.0f)

    let estimateYieldKg parameters damage =
        if damage <= 0 then
            0.0f
        else
            let ratio = float32 damage / parameters.ReferenceDamage

            parameters.ReferenceYieldKg * power ratio parameters.YieldExponent |> max parameters.MinimumYieldKg |> min parameters.MaximumYieldKg

    let pressureRangeCells parameters yieldKg = parameters.RangeCoefficientMetres * cubeRoot yieldKg / parameters.MetresPerCell

    let peakPressureKPa parameters distanceMetres tntEquivalentKg =
        let cubeRootYield = cubeRoot (max tntEquivalentKg parameters.MinimumPressureYieldKg)
        let scaledDistance = max parameters.MinimumScaledDistance (distanceMetres / cubeRootYield)
        let z2 = scaledDistance * scaledDistance
        let z3 = z2 * scaledDistance

        let pressure =
            if scaledDistance < parameters.CloseRangeLimit then
                parameters.CloseCubicCoefficient / z3 + parameters.CloseOffset
            else
                parameters.FarLinearCoefficient / scaledDistance
                + parameters.FarQuadraticCoefficient / z2
                + parameters.FarCubicCoefficient / z3
                + parameters.FarOffset

        max 0.0f (pressure * parameters.PressureUnitKPa)
