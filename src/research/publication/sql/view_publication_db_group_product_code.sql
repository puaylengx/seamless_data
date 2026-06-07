with
    distinct_product_code as (
        SELECT
            TRIM(LOWER(product_code)) AS product_code,
            publication_calendar_year,
            publication_budget_year,
            description,
            division,
            wos_with_jif_p90,
            wos_with_jif,
            wos_sc,
            wos_ss,
            wos_ah,
            wos_es,
            scopus_sjr_10,
            scopus_q1,
            scopus_q2,
            scopus_q3,
            scopus_q4,
            scopus_no_q,
            sense_abc,
            eric,
            math_sci_net,
            pubmed,
            jstor,
            project_muse,
            other_inter,
            tci_group1,
            tci_group2,
            national_international,
            ROW_NUMBER() OVER (
                PARTITION BY
                    TRIM(LOWER(product_code))
                ORDER BY
                    publication_calendar_year DESC,
                    publication_budget_year DESC
            ) AS rn
        FROM
            `Research.publications`
        where
            publication_calendar_year >= 2017
    )
SELECT
    publication_calendar_year,
    publication_budget_year,
    description,
    division,
    wos_with_jif_p90,
    wos_with_jif,
    wos_sc,
    wos_ss,
    wos_ah,
    wos_es,
    scopus_sjr_10,
    scopus_q1,
    scopus_q2,
    scopus_q3,
    scopus_q4,
    scopus_no_q,
    sense_abc,
    eric,
    math_sci_net,
    pubmed,
    jstor,
    project_muse,
    other_inter,
    tci_group1,
    tci_group2,
    national_international,
FROM
    distinct_product_code
WHERE
    rn = 1;