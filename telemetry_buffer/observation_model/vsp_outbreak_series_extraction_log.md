# VSP outbreak series extraction log

Extraction run date: 2026-08-30

## Sources and layouts

- `https://archive.cdc.gov/www_cdc_gov/nceh/vsp/surv/outbreak/archived-outbreaks-1993-2018.html`
- `https://archive.cdc.gov/www_cdc_gov/vessel-sanitation/cruise-ship-outbreaks/earlier-outbreaks-2019-2022.html`
- `https://www.cdc.gov/vessel-sanitation/cruise-ship-outbreaks/index.html`
- `https://www.cdc.gov/vessel-sanitation/cruise-ship-outbreaks/earlier-outbreaks.html`
- `https://web.archive.org/web/20191215062717/https://www.cdc.gov/nceh/vsp/surv/gilist.htm`

| Year | Layout |
|---:|---|
| 1993 | index_counts |
| 1994 | index_counts |
| 1995 | index_counts |
| 1996 | index_counts |
| 1997 | index_counts |
| 1998 | index_counts |
| 1999 | index_counts |
| 2000 | index_counts |
| 2001 | index_counts |
| 2002 | index_counts |
| 2003 | index_counts |
| 2004 | index_counts |
| 2005 | index_counts |
| 2006 | index_counts |
| 2007 | index_counts |
| 2008 | index_counts |
| 2009 | index_counts |
| 2010 | index_counts |
| 2011 | index_counts |
| 2012 | index_counts |
| 2013 | index_counts |
| 2014 | index_counts |
| 2015 | index_counts |
| 2016 | index_counts |
| 2017 | index_counts |
| 2018 | index_counts |
| 2019 | index_counts |
| 2020 | index_counts |
| 2021 | index_counts |
| 2022 | index_counts |
| 2023 | detail_required |
| 2024 | detail_required |
| 2025 | detail_counts |
| 2026 | detail_counts |

Independent cross-check snapshot timestamp: `20191215062717`.

## Row-count check

- Overall: PASS
- 1993: extracted 1; index rows 1
- 1994: extracted 4; index rows 4
- 1995: extracted 3; index rows 3
- 1996: extracted 3; index rows 3
- 1997: extracted 9; index rows 9
- 1998: extracted 9; index rows 9
- 1999: extracted 4; index rows 4
- 2000: extracted 6; index rows 6
- 2001: extracted 4; index rows 4
- 2002: extracted 23; index rows 23
- 2003: extracted 25; index rows 25
- 2004: extracted 36; index rows 36
- 2005: extracted 20; index rows 20
- 2006: extracted 36; index rows 36
- 2007: extracted 24; index rows 24
- 2008: extracted 14; index rows 14
- 2009: extracted 15; index rows 15
- 2010: extracted 14; index rows 14
- 2011: extracted 14; index rows 14
- 2012: extracted 16; index rows 16
- 2013: extracted 9; index rows 9
- 2014: extracted 9; index rows 9
- 2015: extracted 12; index rows 12
- 2016: extracted 13; index rows 13
- 2017: extracted 11; index rows 11
- 2018: extracted 11; index rows 11
- 2019: extracted 10; index rows 10
- 2020: extracted 4; index rows 4
- 2021: extracted 1; index rows 1
- 2022: extracted 4; index rows 4
- 2023: extracted 14; index rows 14
- 2024: extracted 18; index rows 18
- 2025: extracted 23; index rows 23
- 2026: extracted 9; index rows 9

## Rough completeness cross-check

- index years 2004-2019: 264 rows; operator-supplied rough comparison: approximately 261
- index years 2022-2026: 68 rows; operator-supplied rough comparison: approximately 64

## Threshold check

- PASS: threshold rows were counted without filtering them out.
- legacy_pre2004: 0 rows with both printed passenger and crew percentages below 3%
- pre: 0 rows with both printed passenger and crew percentages below 3%
- shutdown: 0 rows with both printed passenger and crew percentages below 3%
- post: 1 rows with both printed passenger and crew percentages below 3%

## Unresolved voyage dates

- 2002 Carnival Pride: March 2002; url=https://archive.cdc.gov/www_cdc_gov/nceh/vsp/surv/outbreak/archived-outbreaks-1993-2018.html
- 2001 Nantucket Clipper: September 2001; url=https://archive.cdc.gov/www_cdc_gov/nceh/vsp/surv/outbreak/archived-outbreaks-1993-2018.html
- 2001 Mississippi: August 2001; url=https://archive.cdc.gov/www_cdc_gov/nceh/vsp/surv/outbreak/archived-outbreaks-1993-2018.html

## 2022 completeness

- PASS: 4 of 4 rows have passenger and crew counts from the CDC-hosted 2019-2022 source `https://archive.cdc.gov/www_cdc_gov/vessel-sanitation/cruise-ship-outbreaks/earlier-outbreaks-2019-2022.html`.

## counts_published breakdown

- full: 313 rows
- passenger_only: 1 rows
- crew_only: 1 rows
- data_not_available: 91 rows
- unparsed: 22 rows

## Cross-source reconciliation

- Hosted-only rows: 8
- web.archive-only rows: 11
- Count disagreements: 7

### Hosted-only rows

- AIDAdiva | 9/5/2019-11/23/2019; hosted_url=https://archive.cdc.gov/www_cdc_gov/vessel-sanitation/cruise-ship-outbreaks/earlier-outbreaks-2019-2022.html; archive_url=https://web.archive.org/web/20191215062717/https://www.cdc.gov/nceh/vsp/surv/gilist.htm
- AIDAdiva | 10/3/2019-11/13/2019; hosted_url=https://archive.cdc.gov/www_cdc_gov/vessel-sanitation/cruise-ship-outbreaks/earlier-outbreaks-2019-2022.html; archive_url=https://web.archive.org/web/20191215062717/https://www.cdc.gov/nceh/vsp/surv/gilist.htm
- Carnival Pride | March 2002; hosted_url=https://archive.cdc.gov/www_cdc_gov/nceh/vsp/surv/outbreak/archived-outbreaks-1993-2018.html; archive_url=https://web.archive.org/web/20191215062717/https://www.cdc.gov/nceh/vsp/surv/gilist.htm
- Jubilee | 6/16/1996-6/23/1996; hosted_url=https://archive.cdc.gov/www_cdc_gov/nceh/vsp/surv/outbreak/archived-outbreaks-1993-2018.html; archive_url=https://web.archive.org/web/20191215062717/https://www.cdc.gov/nceh/vsp/surv/gilist.htm
- Mississippi | August 2001; hosted_url=https://archive.cdc.gov/www_cdc_gov/nceh/vsp/surv/outbreak/archived-outbreaks-1993-2018.html; archive_url=https://web.archive.org/web/20191215062717/https://www.cdc.gov/nceh/vsp/surv/gilist.htm
- Nantucket Clipper | 1/2/1998-1/9/1999; hosted_url=https://archive.cdc.gov/www_cdc_gov/nceh/vsp/surv/outbreak/archived-outbreaks-1993-2018.html; archive_url=https://web.archive.org/web/20191215062717/https://www.cdc.gov/nceh/vsp/surv/gilist.htm
- Nantucket Clipper | September 2001; hosted_url=https://archive.cdc.gov/www_cdc_gov/nceh/vsp/surv/outbreak/archived-outbreaks-1993-2018.html; archive_url=https://web.archive.org/web/20191215062717/https://www.cdc.gov/nceh/vsp/surv/gilist.htm
- Pacific Princess | 12/15/2007-1/10/2008; hosted_url=https://archive.cdc.gov/www_cdc_gov/nceh/vsp/surv/outbreak/archived-outbreaks-1993-2018.html; archive_url=https://web.archive.org/web/20191215062717/https://www.cdc.gov/nceh/vsp/surv/gilist.htm

### web.archive-only rows

- AIDAdiva | 9/5 – 23; hosted_url=https://archive.cdc.gov/www_cdc_gov/vessel-sanitation/cruise-ship-outbreaks/earlier-outbreaks-2019-2022.html; archive_url=https://web.archive.org/web/20191215062717/https://www.cdc.gov/nceh/vsp/surv/outbreak/2019/AIDAdiva_9-5.html
- AIDAdiva | 10/3 – 13; hosted_url=https://archive.cdc.gov/www_cdc_gov/vessel-sanitation/cruise-ship-outbreaks/earlier-outbreaks-2019-2022.html; archive_url=https://web.archive.org/web/20191215062717/https://www.cdc.gov/nceh/vsp/surv/outbreak/2019/AIDAdiva_10-3.html
- American Adventure | 12/26/93-2/2/94; hosted_url=https://archive.cdc.gov/www_cdc_gov/nceh/vsp/surv/outbreak/archived-outbreaks-1993-2018.html; archive_url=https://web.archive.org/web/20191215062717/https://www.cdc.gov/nceh/vsp/surv/gilist.htm
- Carnival Pride | March; hosted_url=https://archive.cdc.gov/www_cdc_gov/nceh/vsp/surv/outbreak/archived-outbreaks-1993-2018.html; archive_url=https://web.archive.org/web/20191215062717/https://www.cdc.gov/nceh/vsp/surv/gilist.htm
- Jubliee | 6/16-6/23; hosted_url=https://archive.cdc.gov/www_cdc_gov/nceh/vsp/surv/outbreak/archived-outbreaks-1993-2018.html; archive_url=https://web.archive.org/web/20191215062717/https://www.cdc.gov/nceh/vsp/surv/gilist.htm
- Mississippi | August; hosted_url=https://archive.cdc.gov/www_cdc_gov/nceh/vsp/surv/outbreak/archived-outbreaks-1993-2018.html; archive_url=https://web.archive.org/web/20191215062717/https://www.cdc.gov/nceh/vsp/surv/gilist.htm
- Nantucket Clipper | 1/2-1/9; hosted_url=https://archive.cdc.gov/www_cdc_gov/nceh/vsp/surv/outbreak/archived-outbreaks-1993-2018.html; archive_url=https://web.archive.org/web/20191215062717/https://www.cdc.gov/nceh/vsp/surv/gilist.htm
- Nantucket Clipper | September; hosted_url=https://archive.cdc.gov/www_cdc_gov/nceh/vsp/surv/outbreak/archived-outbreaks-1993-2018.html; archive_url=https://web.archive.org/web/20191215062717/https://www.cdc.gov/nceh/vsp/surv/gilist.htm
- Ocean Breeze | Investigation done at the request of the cruise line outside the U.S.; hosted_url=https://archive.cdc.gov/www_cdc_gov/nceh/vsp/surv/outbreak/archived-outbreaks-1993-2018.html; archive_url=https://web.archive.org/web/20191215062717/https://www.cdc.gov/nceh/vsp/surv/gilist.htm
- Pacific Princess | 12/15-1/10; hosted_url=https://archive.cdc.gov/www_cdc_gov/nceh/vsp/surv/outbreak/archived-outbreaks-1993-2018.html; archive_url=https://web.archive.org/web/20191215062717/https://www.cdc.gov/nceh/vsp/surv/gilist.htm
- Royal Odyssey | No sail recommendation; hosted_url=https://archive.cdc.gov/www_cdc_gov/nceh/vsp/surv/outbreak/archived-outbreaks-1993-2018.html; archive_url=https://web.archive.org/web/20191215062717/https://www.cdc.gov/nceh/vsp/surv/gilist.htm

### Count disagreements (CDC-hosted values retained)

- Carnival Glory | 10/09/2010-10/16/2010; crew_ill: hosted='20', archive=''; crew_total: hosted='1169', archive=''; hosted_url=https://archive.cdc.gov/www_cdc_gov/nceh/vsp/surv/outbreak/archived-outbreaks-1993-2018.html; archive_url=https://web.archive.org/web/20191215062717/https://www.cdc.gov/nceh/vsp/surv/outbreak/2010/october9glory.htm
- Celebrity Millennium | 04/25/2013-05/10/2013; pax_ill: hosted='23', archive='123'; hosted_url=https://archive.cdc.gov/www_cdc_gov/nceh/vsp/surv/outbreak/archived-outbreaks-1993-2018.html; archive_url=https://web.archive.org/web/20191215062717/https://www.cdc.gov/nceh/vsp/surv/outbreak/2013/may10celebrity_millennium.htm
- Crown Princess | 01/28/2012-02/04/2012; pax_ill: hosted='364', archive=''; pax_total: hosted='3103', archive=''; hosted_url=https://archive.cdc.gov/www_cdc_gov/nceh/vsp/surv/outbreak/archived-outbreaks-1993-2018.html; archive_url=https://web.archive.org/web/20191215062717/https://www.cdc.gov/nceh/vsp/surv/outbreak/2012/feb4crown_princess.htm
- Island Princess | 4/23/2009-5/07/2009; crew_ill: hosted='8', archive='5'; hosted_url=https://archive.cdc.gov/www_cdc_gov/nceh/vsp/surv/outbreak/archived-outbreaks-1993-2018.html; archive_url=https://web.archive.org/web/20191215062717/https://www.cdc.gov/nceh/vsp/surv/outbreak/2009/may6islandprincess.htm
- Mercury | 02/15/2010-02/26/2010; pax_ill: hosted='411', archive=''; pax_total: hosted='1833', archive=''; hosted_url=https://archive.cdc.gov/www_cdc_gov/nceh/vsp/surv/outbreak/archived-outbreaks-1993-2018.html; archive_url=https://web.archive.org/web/20191215062717/https://www.cdc.gov/nceh/vsp/surv/outbreak/2010/february26mercury.htm
- Sea Princess | 05/30/2011-06/09/2011; pax_ill: hosted='14', archive='144'; hosted_url=https://archive.cdc.gov/www_cdc_gov/nceh/vsp/surv/outbreak/archived-outbreaks-1993-2018.html; archive_url=https://web.archive.org/web/20191215062717/https://www.cdc.gov/nceh/vsp/surv/outbreak/2011/june9sea_princess.htm
- Voyager of the Seas | 01/28/2012-02/04/2012; pax_total: hosted='3310', archive='3139'; hosted_url=https://archive.cdc.gov/www_cdc_gov/nceh/vsp/surv/outbreak/archived-outbreaks-1993-2018.html; archive_url=https://web.archive.org/web/20191215062717/https://www.cdc.gov/nceh/vsp/surv/outbreak/2012/feb4voyager.htm

## Agent vocabulary check

- Overall: FAIL (33 invalid values)
- Modal identifier flags:
- None
- Invalid agent values:
- 2017 Crown Princess causative_agent='c. perfringens enterotoxin': url=https://archive.cdc.gov/www_cdc_gov/nceh/vsp/surv/outbreak/archived-outbreaks-1993-2018.html
- 2007 Norwegian Pearl causative_agent='specimens not obtained': url=https://archive.cdc.gov/www_cdc_gov/nceh/vsp/surv/outbreak/archived-outbreaks-1993-2018.html
- 2007 Volendam causative_agent='specimens not obtained': url=https://archive.cdc.gov/www_cdc_gov/nceh/vsp/surv/outbreak/archived-outbreaks-1993-2018.html
- 2007 Volendam causative_agent='specimens not obtained': url=https://archive.cdc.gov/www_cdc_gov/nceh/vsp/surv/outbreak/archived-outbreaks-1993-2018.html
- 2004 Silver Shadow causative_agent='specimens not obtained': url=https://archive.cdc.gov/www_cdc_gov/nceh/vsp/surv/outbreak/archived-outbreaks-1993-2018.html
- 2004 Nantucket Clipper causative_agent='specimens not obtained': url=https://archive.cdc.gov/www_cdc_gov/nceh/vsp/surv/outbreak/archived-outbreaks-1993-2018.html
- 2004 Norwegian Wind causative_agent='specimens not obtained': url=https://archive.cdc.gov/www_cdc_gov/nceh/vsp/surv/outbreak/archived-outbreaks-1993-2018.html
- 2004 The World causative_agent='specimens not obtained': url=https://archive.cdc.gov/www_cdc_gov/nceh/vsp/surv/outbreak/archived-outbreaks-1993-2018.html
- 2004 Queen Elizabeth 2 causative_agent='specimens not obtained': url=https://archive.cdc.gov/www_cdc_gov/nceh/vsp/surv/outbreak/archived-outbreaks-1993-2018.html
- 2004 Legacy causative_agent='specimens not obtained': url=https://archive.cdc.gov/www_cdc_gov/nceh/vsp/surv/outbreak/archived-outbreaks-1993-2018.html
- 2003 Legacy causative_agent='specimens not obtained': url=https://archive.cdc.gov/www_cdc_gov/nceh/vsp/surv/outbreak/archived-outbreaks-1993-2018.html
- 2003 Nantucket Clipper causative_agent='specimens not obtained': url=https://archive.cdc.gov/www_cdc_gov/nceh/vsp/surv/outbreak/archived-outbreaks-1993-2018.html
- 2003 Norwegian Star causative_agent='specimens not obtained': url=https://archive.cdc.gov/www_cdc_gov/nceh/vsp/surv/outbreak/archived-outbreaks-1993-2018.html
- 2003 Clipper Odyssey causative_agent='specimens not obtained': url=https://archive.cdc.gov/www_cdc_gov/nceh/vsp/surv/outbreak/archived-outbreaks-1993-2018.html
- 2003 Rhapsody of the Seas causative_agent='specimens not obtained': url=https://archive.cdc.gov/www_cdc_gov/nceh/vsp/surv/outbreak/archived-outbreaks-1993-2018.html
- 2003 Royal Princess causative_agent='specimens not obtained': url=https://archive.cdc.gov/www_cdc_gov/nceh/vsp/surv/outbreak/archived-outbreaks-1993-2018.html
- 2003 Nantucket Clipper causative_agent='specimens not obtained': url=https://archive.cdc.gov/www_cdc_gov/nceh/vsp/surv/outbreak/archived-outbreaks-1993-2018.html
- 2003 Arabella causative_agent='specimens not obtained': url=https://archive.cdc.gov/www_cdc_gov/nceh/vsp/surv/outbreak/archived-outbreaks-1993-2018.html
- 2002 Nantucket Clipper causative_agent='specimens not obtained': url=https://archive.cdc.gov/www_cdc_gov/nceh/vsp/surv/outbreak/archived-outbreaks-1993-2018.html
- 2002 Norway causative_agent='specimens not obtained': url=https://archive.cdc.gov/www_cdc_gov/nceh/vsp/surv/outbreak/archived-outbreaks-1993-2018.html
- 2002 Seabourn Pride causative_agent='specimens not obtained': url=https://archive.cdc.gov/www_cdc_gov/nceh/vsp/surv/outbreak/archived-outbreaks-1993-2018.html
- 2002 Nantucket Clipper causative_agent='sappovirus': url=https://archive.cdc.gov/www_cdc_gov/nceh/vsp/surv/outbreak/archived-outbreaks-1993-2018.html
- 2002 Norwegian Sun causative_agent='specimens not obtained': url=https://archive.cdc.gov/www_cdc_gov/nceh/vsp/surv/outbreak/archived-outbreaks-1993-2018.html
- 2002 Yorktown Clipper causative_agent='specimens not obtained': url=https://archive.cdc.gov/www_cdc_gov/nceh/vsp/surv/outbreak/archived-outbreaks-1993-2018.html
- 2002 Amsterdam causative_agent='specimens not obtained': url=https://archive.cdc.gov/www_cdc_gov/nceh/vsp/surv/outbreak/archived-outbreaks-1993-2018.html
- 2001 Oriana causative_agent='specimens not obtained': url=https://archive.cdc.gov/www_cdc_gov/nceh/vsp/surv/outbreak/archived-outbreaks-1993-2018.html
- 2000 Palm Beach Princess causative_agent='specimens not obtained': url=https://archive.cdc.gov/www_cdc_gov/nceh/vsp/surv/outbreak/archived-outbreaks-1993-2018.html
- 1998 Vision of the Seas causative_agent='specimens not obtained': url=https://archive.cdc.gov/www_cdc_gov/nceh/vsp/surv/outbreak/archived-outbreaks-1993-2018.html
- 1998 Statendam causative_agent='specimens not obtained': url=https://archive.cdc.gov/www_cdc_gov/nceh/vsp/surv/outbreak/archived-outbreaks-1993-2018.html
- 1997 Zenith causative_agent='specimens not obtained': url=https://archive.cdc.gov/www_cdc_gov/nceh/vsp/surv/outbreak/archived-outbreaks-1993-2018.html
- 1997 Regal Princess causative_agent='specimens not obtained': url=https://archive.cdc.gov/www_cdc_gov/nceh/vsp/surv/outbreak/archived-outbreaks-1993-2018.html
- 1994 Horizon causative_agent='legionella': url=https://archive.cdc.gov/www_cdc_gov/nceh/vsp/surv/outbreak/archived-outbreaks-1993-2018.html
- 1994 Regent Rainbow causative_agent='viral gastroenteritis': url=https://archive.cdc.gov/www_cdc_gov/nceh/vsp/surv/outbreak/archived-outbreaks-1993-2018.html

## Printed-percentage check and triage (checks 1 and 4b)

- Overall: FAIL (19 failures)
- CDC truncating rather than rounding: 5
- CDC error of another kind: 14
- parse error on our side: 0
- 2013 Celebrity Millennium passenger: calculated=1.1717, printed=6.275, classification=CDC error of another kind, url=https://archive.cdc.gov/www_cdc_gov/nceh/vsp/surv/outbreak/archived-outbreaks-1993-2018.html
- 2013 Celebrity Infinity crew: calculated=1.8339, printed=2.05, classification=CDC error of another kind, url=https://archive.cdc.gov/www_cdc_gov/nceh/vsp/surv/outbreak/archived-outbreaks-1993-2018.html
- 2012 Voyager of the Seas passenger: calculated=7.4924, printed=7.90, classification=CDC error of another kind, url=https://archive.cdc.gov/www_cdc_gov/nceh/vsp/surv/outbreak/archived-outbreaks-1993-2018.html
- 2011 Sea Princess passenger: calculated=0.6579, printed=6.77, classification=CDC error of another kind, url=https://archive.cdc.gov/www_cdc_gov/nceh/vsp/surv/outbreak/archived-outbreaks-1993-2018.html
- 2011 National Geographic Sea Lion passenger: calculated=27.8689, printed=28.87, classification=CDC error of another kind, url=https://archive.cdc.gov/www_cdc_gov/nceh/vsp/surv/outbreak/archived-outbreaks-1993-2018.html
- 2011 Coral Princess crew: calculated=0.3436, printed=0.57, classification=CDC error of another kind, url=https://archive.cdc.gov/www_cdc_gov/nceh/vsp/surv/outbreak/archived-outbreaks-1993-2018.html
- 2010 Mercury passenger: calculated=22.1979, printed=22.1, classification=CDC truncating rather than rounding, url=https://archive.cdc.gov/www_cdc_gov/nceh/vsp/surv/outbreak/archived-outbreaks-1993-2018.html
- 2009 Island Princess crew: calculated=0.8949, printed=0.56, classification=CDC error of another kind, url=https://archive.cdc.gov/www_cdc_gov/nceh/vsp/surv/outbreak/archived-outbreaks-1993-2018.html
- 2006 Regal Princess crew: calculated=0.7375, printed=0.07, classification=CDC error of another kind, url=https://archive.cdc.gov/www_cdc_gov/nceh/vsp/surv/outbreak/archived-outbreaks-1993-2018.html
- 2006 Norwegian Wind crew: calculated=1.0130, printed=0.01, classification=CDC error of another kind, url=https://archive.cdc.gov/www_cdc_gov/nceh/vsp/surv/outbreak/archived-outbreaks-1993-2018.html
- 2006 Ryndam passenger: calculated=8.0315, printed=7.97, classification=CDC error of another kind, url=https://archive.cdc.gov/www_cdc_gov/nceh/vsp/surv/outbreak/archived-outbreaks-1993-2018.html
- 2005 Empress of the Seas passenger: calculated=4.6632, printed=4.6, classification=CDC truncating rather than rounding, url=https://archive.cdc.gov/www_cdc_gov/nceh/vsp/surv/outbreak/archived-outbreaks-1993-2018.html
- 2005 Mariner of the Seas passenger: calculated=7.9654, printed=7.9, classification=CDC truncating rather than rounding, url=https://archive.cdc.gov/www_cdc_gov/nceh/vsp/surv/outbreak/archived-outbreaks-1993-2018.html
- 2005 Mariner of the Seas crew: calculated=2.2689, printed=2.2, classification=CDC truncating rather than rounding, url=https://archive.cdc.gov/www_cdc_gov/nceh/vsp/surv/outbreak/archived-outbreaks-1993-2018.html
- 2004 Queen Mary 2 passenger: calculated=1.4726, printed=1.35, classification=CDC error of another kind, url=https://archive.cdc.gov/www_cdc_gov/nceh/vsp/surv/outbreak/archived-outbreaks-1993-2018.html
- 2004 Legacy crew: calculated=4.3478, printed=4.65, classification=CDC error of another kind, url=https://archive.cdc.gov/www_cdc_gov/nceh/vsp/surv/outbreak/archived-outbreaks-1993-2018.html
- 2022 Silver Moon passenger: calculated=2.8791, printed=2.8, classification=CDC truncating rather than rounding, url=https://archive.cdc.gov/www_cdc_gov/vessel-sanitation/cruise-ship-outbreaks/earlier-outbreaks-2019-2022.html
- 2025 Viking Mars passenger: calculated=6.9899, printed=7.2, classification=CDC error of another kind, url=https://www.cdc.gov/vessel-sanitation/cruise-ship-outbreaks/viking-mars-january-2025.html
- 2024 Arcadia passenger: calculated=6.5339, printed=5.57, classification=CDC error of another kind, url=https://www.cdc.gov/vessel-sanitation/cruise-ship-outbreaks/arcadia-september-2024.html

## Plausibility check failures

- Overall: FAIL (13 failures)
- 2017 National Geographic Sea Bird passenger total < 100: url=https://archive.cdc.gov/www_cdc_gov/nceh/vsp/surv/outbreak/archived-outbreaks-1993-2018.html
- 2011 National Geographic Sea Lion passenger total < 100: url=https://archive.cdc.gov/www_cdc_gov/nceh/vsp/surv/outbreak/archived-outbreaks-1993-2018.html
- 2008 Grande Caribe passenger total < 100: url=https://archive.cdc.gov/www_cdc_gov/nceh/vsp/surv/outbreak/archived-outbreaks-1993-2018.html
- 2007 Spirit of Nantucket passenger total < 100: url=https://archive.cdc.gov/www_cdc_gov/nceh/vsp/surv/outbreak/archived-outbreaks-1993-2018.html
- 2004 The World passenger count: url=https://archive.cdc.gov/www_cdc_gov/nceh/vsp/surv/outbreak/archived-outbreaks-1993-2018.html
- 2004 The World passenger total < 100: url=https://archive.cdc.gov/www_cdc_gov/nceh/vsp/surv/outbreak/archived-outbreaks-1993-2018.html
- 2020 Westerdam passenger total < 100: url=https://archive.cdc.gov/www_cdc_gov/vessel-sanitation/cruise-ship-outbreaks/earlier-outbreaks-2019-2022.html
- 2026 National Geographic Sea Bird passenger total < 100: url=https://www.cdc.gov/vessel-sanitation/cruise-ship-outbreaks/national-geographic-sea-bird-july-2026-2.html
- 2026 National Geographic Sea Bird passenger total < 100: url=https://www.cdc.gov/vessel-sanitation/cruise-ship-outbreaks/national-geographic-sea-bird-july-2026.html
- 2026 National Geographic Sea Bird passenger total < 100: url=https://www.cdc.gov/vessel-sanitation/cruise-ship-outbreaks/national-geographic-sea-bird-june-2026.html
- 2026 National Geographic Sea Bird passenger total < 100: url=https://www.cdc.gov/vessel-sanitation/cruise-ship-outbreaks/national-geographic-sea-bird-may-2026.html
- 2025 National Geographic Sea Lion passenger total < 100: url=https://www.cdc.gov/vessel-sanitation/cruise-ship-outbreaks/national-geographic-sea-lion-april-2025.html
- 2025 Sea Cloud Spirit passenger count: url=https://www.cdc.gov/vessel-sanitation/cruise-ship-outbreaks/sea-cloud-spirit-january-2025.html

## Missing or unparseable counts

- 140 field-level gaps were preserved as empty CSV fields.
- 2006 Freedom of the Seas pax_pct_page: https://archive.cdc.gov/www_cdc_gov/nceh/vsp/surv/outbreak/archived-outbreaks-1993-2018.html
- 2005 Ryndam crew_pct_page: https://archive.cdc.gov/www_cdc_gov/nceh/vsp/surv/outbreak/archived-outbreaks-1993-2018.html
- 2004 Nantucket Clipper pax_ill: https://archive.cdc.gov/www_cdc_gov/nceh/vsp/surv/outbreak/archived-outbreaks-1993-2018.html
- 2004 Nantucket Clipper pax_total: https://archive.cdc.gov/www_cdc_gov/nceh/vsp/surv/outbreak/archived-outbreaks-1993-2018.html
- 2004 Nantucket Clipper pax_pct_page: https://archive.cdc.gov/www_cdc_gov/nceh/vsp/surv/outbreak/archived-outbreaks-1993-2018.html
- 2004 Nantucket Clipper crew_ill: https://archive.cdc.gov/www_cdc_gov/nceh/vsp/surv/outbreak/archived-outbreaks-1993-2018.html
- 2004 Nantucket Clipper crew_total: https://archive.cdc.gov/www_cdc_gov/nceh/vsp/surv/outbreak/archived-outbreaks-1993-2018.html
- 2004 Nantucket Clipper crew_pct_page: https://archive.cdc.gov/www_cdc_gov/nceh/vsp/surv/outbreak/archived-outbreaks-1993-2018.html
- 2004 Legacy pax_ill: https://archive.cdc.gov/www_cdc_gov/nceh/vsp/surv/outbreak/archived-outbreaks-1993-2018.html
- 2004 Legacy pax_total: https://archive.cdc.gov/www_cdc_gov/nceh/vsp/surv/outbreak/archived-outbreaks-1993-2018.html
- 2004 Legacy pax_pct_page: https://archive.cdc.gov/www_cdc_gov/nceh/vsp/surv/outbreak/archived-outbreaks-1993-2018.html
- 2026 Insignia pax_ill: https://www.cdc.gov/vessel-sanitation/cruise-ship-outbreaks/oceania-insignia-april-2026.html
- 2026 Insignia pax_total: https://www.cdc.gov/vessel-sanitation/cruise-ship-outbreaks/oceania-insignia-april-2026.html
- 2026 Insignia pax_pct_page: https://www.cdc.gov/vessel-sanitation/cruise-ship-outbreaks/oceania-insignia-april-2026.html
- 2026 Insignia crew_ill: https://www.cdc.gov/vessel-sanitation/cruise-ship-outbreaks/oceania-insignia-april-2026.html
- 2026 Insignia crew_total: https://www.cdc.gov/vessel-sanitation/cruise-ship-outbreaks/oceania-insignia-april-2026.html
- 2026 Insignia crew_pct_page: https://www.cdc.gov/vessel-sanitation/cruise-ship-outbreaks/oceania-insignia-april-2026.html
- 2025 Rotterdam pax_ill: https://www.cdc.gov/vessel-sanitation/cruise-ship-outbreaks/rotterdam-march-2025.html
- 2025 Rotterdam pax_total: https://www.cdc.gov/vessel-sanitation/cruise-ship-outbreaks/rotterdam-march-2025.html
- 2025 Rotterdam pax_pct_page: https://www.cdc.gov/vessel-sanitation/cruise-ship-outbreaks/rotterdam-march-2025.html
- 2025 Rotterdam crew_ill: https://www.cdc.gov/vessel-sanitation/cruise-ship-outbreaks/rotterdam-march-2025.html
- 2025 Rotterdam crew_total: https://www.cdc.gov/vessel-sanitation/cruise-ship-outbreaks/rotterdam-march-2025.html
- 2025 Rotterdam crew_pct_page: https://www.cdc.gov/vessel-sanitation/cruise-ship-outbreaks/rotterdam-march-2025.html
- 2025 Coral Princess crew_ill: https://www.cdc.gov/vessel-sanitation/cruise-ship-outbreaks/coral-princess-february-2025.html
- 2025 Coral Princess crew_total: https://www.cdc.gov/vessel-sanitation/cruise-ship-outbreaks/coral-princess-february-2025.html
- 2025 Coral Princess crew_pct_page: https://www.cdc.gov/vessel-sanitation/cruise-ship-outbreaks/coral-princess-february-2025.html
- 2024 Queen Mary 2 pax_ill: https://www.cdc.gov/vessel-sanitation/cruise-ship-outbreaks/queen-mary-2-december-2024.html
- 2024 Queen Mary 2 pax_total: https://www.cdc.gov/vessel-sanitation/cruise-ship-outbreaks/queen-mary-2-december-2024.html
- 2024 Queen Mary 2 pax_pct_page: https://www.cdc.gov/vessel-sanitation/cruise-ship-outbreaks/queen-mary-2-december-2024.html
- 2024 Queen Mary 2 crew_ill: https://www.cdc.gov/vessel-sanitation/cruise-ship-outbreaks/queen-mary-2-december-2024.html
- 2024 Queen Mary 2 crew_total: https://www.cdc.gov/vessel-sanitation/cruise-ship-outbreaks/queen-mary-2-december-2024.html
- 2024 Queen Mary 2 crew_pct_page: https://www.cdc.gov/vessel-sanitation/cruise-ship-outbreaks/queen-mary-2-december-2024.html
- 2024 Coral Princess pax_ill: https://www.cdc.gov/vessel-sanitation/cruise-ship-outbreaks/coral-princess-october-2024.html
- 2024 Coral Princess pax_total: https://www.cdc.gov/vessel-sanitation/cruise-ship-outbreaks/coral-princess-october-2024.html
- 2024 Coral Princess pax_pct_page: https://www.cdc.gov/vessel-sanitation/cruise-ship-outbreaks/coral-princess-october-2024.html
- 2024 Coral Princess crew_ill: https://www.cdc.gov/vessel-sanitation/cruise-ship-outbreaks/coral-princess-october-2024.html
- 2024 Coral Princess crew_total: https://www.cdc.gov/vessel-sanitation/cruise-ship-outbreaks/coral-princess-october-2024.html
- 2024 Coral Princess crew_pct_page: https://www.cdc.gov/vessel-sanitation/cruise-ship-outbreaks/coral-princess-october-2024.html
- 2024 Radiance of the Seas pax_ill: https://www.cdc.gov/vessel-sanitation/cruise-ship-outbreaks/radiance-of-the-seas-april-2024.html
- 2024 Radiance of the Seas pax_total: https://www.cdc.gov/vessel-sanitation/cruise-ship-outbreaks/radiance-of-the-seas-april-2024.html
- 2024 Radiance of the Seas pax_pct_page: https://www.cdc.gov/vessel-sanitation/cruise-ship-outbreaks/radiance-of-the-seas-april-2024.html
- 2024 Radiance of the Seas crew_ill: https://www.cdc.gov/vessel-sanitation/cruise-ship-outbreaks/radiance-of-the-seas-april-2024.html
- 2024 Radiance of the Seas crew_total: https://www.cdc.gov/vessel-sanitation/cruise-ship-outbreaks/radiance-of-the-seas-april-2024.html
- 2024 Radiance of the Seas crew_pct_page: https://www.cdc.gov/vessel-sanitation/cruise-ship-outbreaks/radiance-of-the-seas-april-2024.html
- 2024 Silver Nova pax_ill: https://www.cdc.gov/vessel-sanitation/cruise-ship-outbreaks/silver-nova-march-2024.html
- 2024 Silver Nova pax_total: https://www.cdc.gov/vessel-sanitation/cruise-ship-outbreaks/silver-nova-march-2024.html
- 2024 Silver Nova pax_pct_page: https://www.cdc.gov/vessel-sanitation/cruise-ship-outbreaks/silver-nova-march-2024.html
- 2024 Silver Nova crew_ill: https://www.cdc.gov/vessel-sanitation/cruise-ship-outbreaks/silver-nova-march-2024.html
- 2024 Silver Nova crew_total: https://www.cdc.gov/vessel-sanitation/cruise-ship-outbreaks/silver-nova-march-2024.html
- 2024 Silver Nova crew_pct_page: https://www.cdc.gov/vessel-sanitation/cruise-ship-outbreaks/silver-nova-march-2024.html
- 2024 Koningsdam pax_ill: https://www.cdc.gov/vessel-sanitation/cruise-ship-outbreaks/koningsdam-february-2024.html
- 2024 Koningsdam pax_total: https://www.cdc.gov/vessel-sanitation/cruise-ship-outbreaks/koningsdam-february-2024.html
- 2024 Koningsdam pax_pct_page: https://www.cdc.gov/vessel-sanitation/cruise-ship-outbreaks/koningsdam-february-2024.html
- 2024 Koningsdam crew_ill: https://www.cdc.gov/vessel-sanitation/cruise-ship-outbreaks/koningsdam-february-2024.html
- 2024 Koningsdam crew_total: https://www.cdc.gov/vessel-sanitation/cruise-ship-outbreaks/koningsdam-february-2024.html
- 2024 Koningsdam crew_pct_page: https://www.cdc.gov/vessel-sanitation/cruise-ship-outbreaks/koningsdam-february-2024.html
- 2023 Scarlet Lady pax_ill: https://www.cdc.gov/vessel-sanitation/cruise-ship-outbreaks/scarlet-lady-october-2023.html
- 2023 Scarlet Lady pax_total: https://www.cdc.gov/vessel-sanitation/cruise-ship-outbreaks/scarlet-lady-october-2023.html
- 2023 Scarlet Lady pax_pct_page: https://www.cdc.gov/vessel-sanitation/cruise-ship-outbreaks/scarlet-lady-october-2023.html
- 2023 Scarlet Lady crew_ill: https://www.cdc.gov/vessel-sanitation/cruise-ship-outbreaks/scarlet-lady-october-2023.html
- 2023 Scarlet Lady crew_total: https://www.cdc.gov/vessel-sanitation/cruise-ship-outbreaks/scarlet-lady-october-2023.html
- 2023 Scarlet Lady crew_pct_page: https://www.cdc.gov/vessel-sanitation/cruise-ship-outbreaks/scarlet-lady-october-2023.html
- 2023 Viking Neptune pax_ill: https://www.cdc.gov/vessel-sanitation/cruise-ship-outbreaks/viking-neptune-june-2023.html
- 2023 Viking Neptune pax_total: https://www.cdc.gov/vessel-sanitation/cruise-ship-outbreaks/viking-neptune-june-2023.html
- 2023 Viking Neptune pax_pct_page: https://www.cdc.gov/vessel-sanitation/cruise-ship-outbreaks/viking-neptune-june-2023.html
- 2023 Viking Neptune crew_ill: https://www.cdc.gov/vessel-sanitation/cruise-ship-outbreaks/viking-neptune-june-2023.html
- 2023 Viking Neptune crew_total: https://www.cdc.gov/vessel-sanitation/cruise-ship-outbreaks/viking-neptune-june-2023.html
- 2023 Viking Neptune crew_pct_page: https://www.cdc.gov/vessel-sanitation/cruise-ship-outbreaks/viking-neptune-june-2023.html
- 2023 Celebrity Summit pax_ill: https://www.cdc.gov/vessel-sanitation/cruise-ship-outbreaks/celebrity-summit-may-2023.html
- 2023 Celebrity Summit pax_total: https://www.cdc.gov/vessel-sanitation/cruise-ship-outbreaks/celebrity-summit-may-2023.html
- 2023 Celebrity Summit pax_pct_page: https://www.cdc.gov/vessel-sanitation/cruise-ship-outbreaks/celebrity-summit-may-2023.html
- 2023 Celebrity Summit crew_ill: https://www.cdc.gov/vessel-sanitation/cruise-ship-outbreaks/celebrity-summit-may-2023.html
- 2023 Celebrity Summit crew_total: https://www.cdc.gov/vessel-sanitation/cruise-ship-outbreaks/celebrity-summit-may-2023.html
- 2023 Celebrity Summit crew_pct_page: https://www.cdc.gov/vessel-sanitation/cruise-ship-outbreaks/celebrity-summit-may-2023.html
- 2023 Nieuw Amsterdam pax_ill: https://www.cdc.gov/vessel-sanitation/cruise-ship-outbreaks/nieuw-amsterdam-may-2023.html
- 2023 Nieuw Amsterdam pax_total: https://www.cdc.gov/vessel-sanitation/cruise-ship-outbreaks/nieuw-amsterdam-may-2023.html
- 2023 Nieuw Amsterdam pax_pct_page: https://www.cdc.gov/vessel-sanitation/cruise-ship-outbreaks/nieuw-amsterdam-may-2023.html
- 2023 Nieuw Amsterdam crew_ill: https://www.cdc.gov/vessel-sanitation/cruise-ship-outbreaks/nieuw-amsterdam-may-2023.html
- 2023 Nieuw Amsterdam crew_total: https://www.cdc.gov/vessel-sanitation/cruise-ship-outbreaks/nieuw-amsterdam-may-2023.html
- 2023 Nieuw Amsterdam crew_pct_page: https://www.cdc.gov/vessel-sanitation/cruise-ship-outbreaks/nieuw-amsterdam-may-2023.html
- 2023 Grand Princess pax_ill: https://www.cdc.gov/vessel-sanitation/cruise-ship-outbreaks/grand-princess-march-2023.html
- 2023 Grand Princess pax_total: https://www.cdc.gov/vessel-sanitation/cruise-ship-outbreaks/grand-princess-march-2023.html
- 2023 Grand Princess pax_pct_page: https://www.cdc.gov/vessel-sanitation/cruise-ship-outbreaks/grand-princess-march-2023.html
- 2023 Grand Princess crew_ill: https://www.cdc.gov/vessel-sanitation/cruise-ship-outbreaks/grand-princess-march-2023.html
- 2023 Grand Princess crew_total: https://www.cdc.gov/vessel-sanitation/cruise-ship-outbreaks/grand-princess-march-2023.html
- 2023 Grand Princess crew_pct_page: https://www.cdc.gov/vessel-sanitation/cruise-ship-outbreaks/grand-princess-march-2023.html
- 2023 Emerald Princess pax_ill: https://www.cdc.gov/vessel-sanitation/cruise-ship-outbreaks/emerald-princess-march-2023.html
- 2023 Emerald Princess pax_total: https://www.cdc.gov/vessel-sanitation/cruise-ship-outbreaks/emerald-princess-march-2023.html
- 2023 Emerald Princess pax_pct_page: https://www.cdc.gov/vessel-sanitation/cruise-ship-outbreaks/emerald-princess-march-2023.html
- 2023 Emerald Princess crew_ill: https://www.cdc.gov/vessel-sanitation/cruise-ship-outbreaks/emerald-princess-march-2023.html
- 2023 Emerald Princess crew_total: https://www.cdc.gov/vessel-sanitation/cruise-ship-outbreaks/emerald-princess-march-2023.html
- 2023 Emerald Princess crew_pct_page: https://www.cdc.gov/vessel-sanitation/cruise-ship-outbreaks/emerald-princess-march-2023.html
- 2023 Enchantment of the Seas pax_ill: https://www.cdc.gov/vessel-sanitation/cruise-ship-outbreaks/enchantment-of-the-seas-march-2023.html
- 2023 Enchantment of the Seas pax_total: https://www.cdc.gov/vessel-sanitation/cruise-ship-outbreaks/enchantment-of-the-seas-march-2023.html
- 2023 Enchantment of the Seas pax_pct_page: https://www.cdc.gov/vessel-sanitation/cruise-ship-outbreaks/enchantment-of-the-seas-march-2023.html
- 2023 Enchantment of the Seas crew_ill: https://www.cdc.gov/vessel-sanitation/cruise-ship-outbreaks/enchantment-of-the-seas-march-2023.html
- 2023 Enchantment of the Seas crew_total: https://www.cdc.gov/vessel-sanitation/cruise-ship-outbreaks/enchantment-of-the-seas-march-2023.html
- 2023 Enchantment of the Seas crew_pct_page: https://www.cdc.gov/vessel-sanitation/cruise-ship-outbreaks/enchantment-of-the-seas-march-2023.html
- 2023 Enchantment of the Seas pax_ill: https://www.cdc.gov/vessel-sanitation/cruise-ship-outbreaks/enchantment-of-the-seas-march-2023.html
- 2023 Enchantment of the Seas pax_total: https://www.cdc.gov/vessel-sanitation/cruise-ship-outbreaks/enchantment-of-the-seas-march-2023.html
- 2023 Enchantment of the Seas pax_pct_page: https://www.cdc.gov/vessel-sanitation/cruise-ship-outbreaks/enchantment-of-the-seas-march-2023.html
- 2023 Enchantment of the Seas crew_ill: https://www.cdc.gov/vessel-sanitation/cruise-ship-outbreaks/enchantment-of-the-seas-march-2023.html
- 2023 Enchantment of the Seas crew_total: https://www.cdc.gov/vessel-sanitation/cruise-ship-outbreaks/enchantment-of-the-seas-march-2023.html
- 2023 Enchantment of the Seas crew_pct_page: https://www.cdc.gov/vessel-sanitation/cruise-ship-outbreaks/enchantment-of-the-seas-march-2023.html
- 2023 Celebrity Equinox pax_ill: https://www.cdc.gov/vessel-sanitation/cruise-ship-outbreaks/celebrity-equinox-march-2023.html
- 2023 Celebrity Equinox pax_total: https://www.cdc.gov/vessel-sanitation/cruise-ship-outbreaks/celebrity-equinox-march-2023.html
- 2023 Celebrity Equinox pax_pct_page: https://www.cdc.gov/vessel-sanitation/cruise-ship-outbreaks/celebrity-equinox-march-2023.html
- 2023 Celebrity Equinox crew_ill: https://www.cdc.gov/vessel-sanitation/cruise-ship-outbreaks/celebrity-equinox-march-2023.html
- 2023 Celebrity Equinox crew_total: https://www.cdc.gov/vessel-sanitation/cruise-ship-outbreaks/celebrity-equinox-march-2023.html
- 2023 Celebrity Equinox crew_pct_page: https://www.cdc.gov/vessel-sanitation/cruise-ship-outbreaks/celebrity-equinox-march-2023.html
- 2023 Celebrity Constellation pax_ill: https://www.cdc.gov/vessel-sanitation/cruise-ship-outbreaks/celebrity-constellation-march-2023.html
- 2023 Celebrity Constellation pax_total: https://www.cdc.gov/vessel-sanitation/cruise-ship-outbreaks/celebrity-constellation-march-2023.html
- 2023 Celebrity Constellation pax_pct_page: https://www.cdc.gov/vessel-sanitation/cruise-ship-outbreaks/celebrity-constellation-march-2023.html
- 2023 Celebrity Constellation crew_ill: https://www.cdc.gov/vessel-sanitation/cruise-ship-outbreaks/celebrity-constellation-march-2023.html
- 2023 Celebrity Constellation crew_total: https://www.cdc.gov/vessel-sanitation/cruise-ship-outbreaks/celebrity-constellation-march-2023.html
- 2023 Celebrity Constellation crew_pct_page: https://www.cdc.gov/vessel-sanitation/cruise-ship-outbreaks/celebrity-constellation-march-2023.html
- 2023 Ruby Princess pax_ill: https://www.cdc.gov/vessel-sanitation/cruise-ship-outbreaks/ruby-princess-february-2023.html
- 2023 Ruby Princess pax_total: https://www.cdc.gov/vessel-sanitation/cruise-ship-outbreaks/ruby-princess-february-2023.html
- 2023 Ruby Princess pax_pct_page: https://www.cdc.gov/vessel-sanitation/cruise-ship-outbreaks/ruby-princess-february-2023.html
- 2023 Ruby Princess crew_ill: https://www.cdc.gov/vessel-sanitation/cruise-ship-outbreaks/ruby-princess-february-2023.html
- 2023 Ruby Princess crew_total: https://www.cdc.gov/vessel-sanitation/cruise-ship-outbreaks/ruby-princess-february-2023.html
- 2023 Ruby Princess crew_pct_page: https://www.cdc.gov/vessel-sanitation/cruise-ship-outbreaks/ruby-princess-february-2023.html
- 2023 Jewel of the Seas pax_ill: https://www.cdc.gov/vessel-sanitation/cruise-ship-outbreaks/jewel-of-the-seas-january-2023.html
- 2023 Jewel of the Seas pax_total: https://www.cdc.gov/vessel-sanitation/cruise-ship-outbreaks/jewel-of-the-seas-january-2023.html
- 2023 Jewel of the Seas pax_pct_page: https://www.cdc.gov/vessel-sanitation/cruise-ship-outbreaks/jewel-of-the-seas-january-2023.html
- 2023 Jewel of the Seas crew_ill: https://www.cdc.gov/vessel-sanitation/cruise-ship-outbreaks/jewel-of-the-seas-january-2023.html
- 2023 Jewel of the Seas crew_total: https://www.cdc.gov/vessel-sanitation/cruise-ship-outbreaks/jewel-of-the-seas-january-2023.html
- 2023 Jewel of the Seas crew_pct_page: https://www.cdc.gov/vessel-sanitation/cruise-ship-outbreaks/jewel-of-the-seas-january-2023.html
- 2023 Brilliance of the Seas pax_ill: https://www.cdc.gov/vessel-sanitation/cruise-ship-outbreaks/brilliance-of-the-seas-january-2023.html
- 2023 Brilliance of the Seas pax_total: https://www.cdc.gov/vessel-sanitation/cruise-ship-outbreaks/brilliance-of-the-seas-january-2023.html
- 2023 Brilliance of the Seas pax_pct_page: https://www.cdc.gov/vessel-sanitation/cruise-ship-outbreaks/brilliance-of-the-seas-january-2023.html
- 2023 Brilliance of the Seas crew_ill: https://www.cdc.gov/vessel-sanitation/cruise-ship-outbreaks/brilliance-of-the-seas-january-2023.html
- 2023 Brilliance of the Seas crew_total: https://www.cdc.gov/vessel-sanitation/cruise-ship-outbreaks/brilliance-of-the-seas-january-2023.html
- 2023 Brilliance of the Seas crew_pct_page: https://www.cdc.gov/vessel-sanitation/cruise-ship-outbreaks/brilliance-of-the-seas-january-2023.html
- 2023 Arcadia pax_ill: https://www.cdc.gov/vessel-sanitation/cruise-ship-outbreaks/arcadia-january-2023.html
- 2023 Arcadia pax_total: https://www.cdc.gov/vessel-sanitation/cruise-ship-outbreaks/arcadia-january-2023.html
- 2023 Arcadia pax_pct_page: https://www.cdc.gov/vessel-sanitation/cruise-ship-outbreaks/arcadia-january-2023.html
- 2023 Arcadia crew_ill: https://www.cdc.gov/vessel-sanitation/cruise-ship-outbreaks/arcadia-january-2023.html
- 2023 Arcadia crew_total: https://www.cdc.gov/vessel-sanitation/cruise-ship-outbreaks/arcadia-january-2023.html
- 2023 Arcadia crew_pct_page: https://www.cdc.gov/vessel-sanitation/cruise-ship-outbreaks/arcadia-january-2023.html

## Idempotence check

- PASS: the script re-runs extraction from the raw cache and compares the resulting CSV bytes.
