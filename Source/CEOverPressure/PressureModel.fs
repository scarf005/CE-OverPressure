namespace CEOverPressure

open System

module internal PressureModel =
    [<Literal>]
    let MetresPerCell = 0.8f

    [<Literal>]
    let ReferenceDamage = 217.0f

    [<Literal>]
    let ReferenceYieldKg = 2.2f

    let private power value exponent = Math.Pow(float value, float exponent) |> float32
    let private cubeRoot value = power value (1.0f / 3.0f)

    let estimateYieldKg damage =
        if damage <= 0 then
            0.0f
        else
            let ratio = float32 damage / ReferenceDamage
            ReferenceYieldKg * power ratio 1.35f |> max 0.02f |> min 1000.0f

    let pressureRangeCells yieldKg = 8.0f * cubeRoot yieldKg / MetresPerCell

    let peakPressureKPa distanceMetres tntEquivalentKg =
        let cubeRootYield = cubeRoot (max tntEquivalentKg 0.001f)
        let scaledDistance = max 0.25f (distanceMetres / cubeRootYield)
        let z2 = scaledDistance * scaledDistance
        let z3 = z2 * scaledDistance

        let pressureBar = if scaledDistance < 1.35f then 6.7f / z3 + 1.0f else 0.975f / scaledDistance + 1.455f / z2 + 5.85f / z3 - 0.019f

        max 0.0f (pressureBar * 100.0f)
