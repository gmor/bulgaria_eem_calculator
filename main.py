import pandas as pd
import numpy_financial as npf
import itertools

df = pd.read_pickle("measures.pkl")

#def bulgaria_eem_calculator(df):

lifespan_by_eem = {
    "BuildingFabricMeasure": 25,
    "BuildingFabricMeasure.FloorMeasure": 25,
    "BuildingFabricMeasure.RoofAndCeilingMeasure": 25,
    "BuildingFabricMeasure.WallMeasure.WallCavityInsulation": 25,
    "LightingMeasure": 10,
    "RenewableGenerationMeasure": 25,
    "HVACAndHotWaterMeasure.CombinedHeatingCoolingSystemMeasure.HeatingAndCoolingDistributionMeasure.HeatingAndCoolingDistributionSystemReplacement": 15,
    "HVACAndHotWaterMeasure": 15,
    "default": 10
}
columns_mapping = {
    "eem_subject": "eem_subject",
    "eem_type": "eem_type",
    "Investments": "eem_investment",
    "Savings_Electricity": "EnergyUseSavings~EnergyConsumptionGridElectricity~KiloW-H",
    "Savings_Emission reduction": "EmissionsSavings~EnergyConsumptionTotal~KiloGM-CO2",
    "Savings_Finacial savings": "EnergyCostSavings~EnergyConsumptionTotal~BGN",
    "Savings_Gas": "EnergyUseSavings~EnergyConsumptionGas~KiloW-H",
    "Savings_Hard fuels": "EnergyUseSavings~EnergyConsumptionCoal~KiloW-H",
    "Savings_Heat energy": "EnergyUseSavings~EnergyConsumptionDistrictHeating~KiloW-H",
    "Savings_Liquid fuels": "EnergyUseSavings~EnergyConsumptionOil~KiloW-H",
    "Savings_Others": "EnergyUseSavings~EnergyConsumptionOthers~KiloW-H",
    "Savings_Total": "EnergyUseSavings~EnergyConsumptionTotal~KiloW-H",
    "subject": "building_id",
    "epc_date": "start",
    "GFA, m2": "building_area"
}
kpis = ["EnergyUseSavings","EmissionsSavings","EnergyCostSavings"]
discount_rate = 0.05

# Get EEM types and change column names
eem_type = df.eem_subject.str.split("-", expand=True)[[2]]
eem_type.columns = ["eem_type"]
df = pd.concat([df,eem_type],axis=1)
df = df.drop(columns = df.columns.difference(list(columns_mapping.keys())))
df.columns = list(pd.Series(df.columns).replace(columns_mapping,regex=False))

# Add the lifespan and discount_rate
df.index = df.eem_type
df["lifespan"] = lifespan_by_eem
df = df.reset_index(drop=True)
df["discount_rate"] = discount_rate

# Cast to correct class
df["eem_investment"] = pd.to_numeric(df["eem_investment"], errors='coerce')
df['building_area'] = pd.to_numeric(df["building_area"], errors='coerce')
df['start'] = pd.to_datetime(df["start"], errors='coarce')
kpi_columns = list(filter(lambda i: i.startswith(tuple(kpis)), list(df.columns)))
for kpi_item in kpi_columns:
    df[kpi_item] = pd.to_numeric(df[kpi_item], errors='coerce')

# Generate all the area-normalised KPIs
#non_kpi_columns = list(filter(lambda i: np.logical_not(i.startswith(tuple(kpis))), list(df.columns)))
suffix_kpi = "Intensity"
suffix_unit_kpi = "-M2"
for kpi_item in kpi_columns:
    kpi_items = kpi_item.split("~")
    kpi_name = f"{kpi_items[0]}{suffix_kpi}"
    kpi_unit = f"{kpi_items[2]}{suffix_unit_kpi}"
    if kpi_name not in kpis:
        kpis.append(kpi_name)
    df[f"{kpi_name}~{kpi_items[1]}~{kpi_unit}"] = \
        df[kpi_item]/pd.to_numeric(df["building_area"], errors='coerce')

df["NormalisedInvestmentCost~~BGN-M2"] = df["eem_investment"]/df["building_area"]
kpis.append("NormalisedInvestmentCost")

df["AvoidanceCost~~BGN-KiloW-H"] = \
    df["eem_investment"] / (df["EnergyUseSavings~EnergyConsumptionTotal~KiloW-H"] * df["lifespan"])
kpis.append("AvoidanceCost")

df["SimplePayback~~years"] = \
    df["eem_investment"] / (df["EnergyCostSavings~EnergyConsumptionTotal~BGN"])
kpis.append("SimplePayback")

df["NetPresentValue~~BGN"] = df.apply(
    lambda x:
        npf.npv(x['discount_rate'],
                list(itertools.chain(
                    [-x['eem_investment']],
                    list(itertools.repeat(x['EnergyCostSavings~EnergyConsumptionTotal~BGN'],x['lifespan'])) ))),
    axis=1
)
kpis.append("NetPresentValue")

df["ProfitabilityIndex~~"] = (df["NetPresentValue~~BGN"] - df["eem_investment"]) / df["eem_investment"]
kpis.append("ProfitabilityIndex")

df["NetPresentValueQuotient~~"] = df["NetPresentValue~~BGN"] / df["eem_investment"]
kpis.append("NetPresentValueQuotient")

df["InternalRateOfReturn~~PERCENT"] = df.apply(
    lambda x:
        npf.irr(list(itertools.chain(
                    [-x['eem_investment']],
                    list(itertools.repeat(x['EnergyCostSavings~EnergyConsumptionTotal~BGN'],x['lifespan'])) ))),
    axis=1
)
kpis.append("NetPresentValueQuotient")