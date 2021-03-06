from __future__ import division

from risk_models.claus.claus_tables import (
    ONE_FIRST_DEG_TABLE,
    ONE_SECOND_DEG_TABLE,
    TWO_FIRST_DEG_TABLE,
    MOTHER_MATERNAL_AUNT,
    MOTHER_PATERNAL_AUNT,
    TWO_SEC_DEG_DIFF_SIDE_TABLE,
    TWO_SEC_DEG_SAME_SIDE_TABLE,
)

VALID_MIN_AGE = 20
VALID_MAX_AGE = 79


def calculate_risk(patient_age,
                   mother_onset_age=[],
                   daughter_onset_ages=[],
                   full_sister_onset_ages=[],
                   maternal_aunt_onset_ages=[],
                   paternal_aunt_onset_ages=[],
                   maternal_grandmother_onset_ages=[],
                   paternal_grandmother_onset_ages=[],
                   maternal_half_sister_onset_ages=[],
                   paternal_half_sister_onset_ages=[]):
    """
    Calculates the lifteime claus risk score based on age of relatives' breast cancer onset and
    the patient's current cancer-free age.
    """

    if VALID_MAX_AGE < patient_age < VALID_MIN_AGE:
        return None

    # Support mother's age being loaded in as an int instead of a list
    first_degree_ages = [mother_onset_age] if mother_onset_age else []
    first_degree_ages = sort_ages([
        x for x in
        first_degree_ages +
        full_sister_onset_ages +
        daughter_onset_ages
        if x
    ])

    # Assemble the age categories and do an ascending sort
    second_degree_ages = sort_ages([
        x for x in
        maternal_aunt_onset_ages +
        paternal_aunt_onset_ages +
        maternal_grandmother_onset_ages +
        paternal_grandmother_onset_ages +
        maternal_half_sister_onset_ages +
        paternal_half_sister_onset_ages
        if x
    ])

    maternal_second_degree_ages = sort_ages([
        x for x in
        maternal_aunt_onset_ages +
        maternal_grandmother_onset_ages +
        maternal_half_sister_onset_ages
        if x
    ])

    paternal_second_degree_ages = sort_ages([
        x for x in
        paternal_aunt_onset_ages +
        paternal_grandmother_onset_ages +
        paternal_half_sister_onset_ages
        if x
    ])

    risk = 0

    # Check for one 1st or 2nd degree relative
    for ages, table in ((first_degree_ages, ONE_FIRST_DEG_TABLE),
                        (second_degree_ages, ONE_SECOND_DEG_TABLE)):
        if ages:
            risk = max(risk, get_lifetime_risk(
                                        table, patient_age,
                                        _bin_age_to_index(ages[0])))

    # Check for mother and an aunt
    if mother_onset_age:
        for ages, table in ((maternal_aunt_onset_ages, MOTHER_MATERNAL_AUNT),
                            (paternal_aunt_onset_ages, MOTHER_PATERNAL_AUNT)):
            ages = sort_ages(ages)
            if ages:
                risk = max(risk, get_lifetime_risk(
                                            table, patient_age,
                                            _bin_age_to_index(mother_onset_age),
                                            _bin_age_to_index(ages[0])))

    # Check for relatives that are both 1st degree or both 2nd degree and on the same side
    for ages, table in ((first_degree_ages, TWO_FIRST_DEG_TABLE),
                        (maternal_second_degree_ages, TWO_SEC_DEG_SAME_SIDE_TABLE),
                        (paternal_second_degree_ages, TWO_SEC_DEG_SAME_SIDE_TABLE)):
        if len(ages) > 1:
            risk = max(risk, get_lifetime_risk(
                                        table, patient_age,
                                        _bin_age_to_index(ages[0]),
                                        _bin_age_to_index(ages[1])))

    # Check for two relatives that are on opposite sides
    if maternal_second_degree_ages and paternal_second_degree_ages:
        risk = max(risk, get_lifetime_risk(
                       TWO_SEC_DEG_DIFF_SIDE_TABLE, patient_age,
                       _bin_age_to_index(maternal_second_degree_ages[0]),
                       _bin_age_to_index(paternal_second_degree_ages[0])))

    return risk if risk > 0 else None


def get_lifetime_risk(table,
                      patient_age,
                      relative1_index,
                      relative2_index=None):
    """
    Computes the conditional risk of patient getting cancer by age 79 given that the patient
    has been cancer free until current age. Inputs are the correct claus table to use and the
    relatives's age index into the table.

    Calculates from lifetime expected risk and the expected risk of patient's current age.
    For patients current age, we look at the claus table of age range below and above the current age.
    Then take a linear interpolation to estimate the current value.

    EX: for age 33. We look up risk at 29 and 39. then estimate assuming risk at age 33 assuming linear change
    between those 10 years.
    """
    lifetime_risk = _lookup_claus_table(table, -1, relative1_index, relative2_index)

    # Get lower age bin index on table as well number of years over that lower bin
    patient_age_lower_bin_index, patient_age_over_bin = divmod(patient_age - 29, 10)

    current_age_risk = _lookup_claus_table(table, patient_age_lower_bin_index, relative1_index, relative2_index)

    if patient_age_over_bin:
        patient_age_upper_bin_risk = _lookup_claus_table(table, patient_age_lower_bin_index + 1, relative1_index, relative2_index)
        current_age_risk += (patient_age_upper_bin_risk - current_age_risk) * patient_age_over_bin / 10

    return round((lifetime_risk - current_age_risk) / (1 - current_age_risk), 3)


def _lookup_claus_table(table, patient_index, relative1_index, relative2_index=None):
    if relative2_index is not None:
        return table[patient_index][relative1_index][relative2_index]
    return table[patient_index][relative1_index]


def sort_ages(ages):
    return sorted([age for age in ages if VALID_MAX_AGE >= age >= VALID_MIN_AGE])


def _bin_age_to_index(age):
    return None if not age else (age - 20) // 10
