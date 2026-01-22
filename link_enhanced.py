# %%
import pandas as pd
pd.set_option('display.max_columns', None)

# ---------------------------
# CONSTANTS & FILTER LISTS
# ---------------------------

VALID_SUBSCRIBER_TYPES = [
    'beIN', 'beIN Quartar Installment', 'CNE Subscriber', 'BeIN sports CC',
    'beIN Bi Installment', 'Corporate Subscriber', 'Bein NC',
    'beIN Installment Sub', 'beIN Dealer', 'Charge Back', 'Head End',
    'Illegal Network', 'Outsiders', 'VIP_CNE'
]

VALID_INVOICE_TYPES = ['Subscription Invoice']
TAX_COLUMNS = [
    'Subscriber Number', 'Amount', 'Docinternalid', 'Receiptno',
    'Created Date', 'Subscriber Type Name', 'Item Eng Name', 'Payment Flag Id'
]

VALID_TAX_ITEMS = ['Sub.beiN']
EXCLUDED_JV_TYPES = ['Debit']
VALID_PAYMENT_FLAGS = ['Automation', 'Normal payment']

INVOICE_OUTPUT_COLUMNS = [
    'inv_Subscriber Nr', 'inv_Doc Type', 'inv_Ftnr', 'inv_Created Date',
    'inv_Created Time', 'inv_Doc Status', 'inv_Period From',
    'inv_Period To', 'inv_Amount', 'inv_User Name',
    'inv_Default Entity Type', 'inv_Smartcard', 'inv_Bill Period',
    'inv_Bill Cycle', 'inv_Invoice Type', 'inv_Plan Name',
    'inv_Contract Number', 'inv_Subscriber Type',
    'inv_Subscriber Entity', 'pmt_Amount', 'pmt_Ftnr',
    'Docinternalid', 'flag'
]


# ---------------------------
# HELPER FUNCTIONS
# ---------------------------

def assign_unique_payment_pairs(group):
    """Match each group of payment FTNRs to tax Docinternalid one-to-one."""
    unique_payment_ids = group['pmt_Ftnr'].unique()
    unique_tax_ids = group['Docinternalid_y'].unique()

    pair_count = min(len(unique_payment_ids), len(unique_tax_ids))

    return pd.DataFrame({
        'pmt_Subscriber Nr': group.name[0],
        'pmt_Doc Type': group.name[1],
        'pmt_Ftnr': unique_payment_ids[:pair_count],
        'Docinternalid_y': unique_tax_ids[:pair_count]
    })


def assign_unique_invoice_pairs(group):
    """Match each invoice FTNR with its payment FTNR."""
    unique_payment_ftnr = group['pmt_Ftnr'].unique()
    unique_invoice_ftnr = group['inv_Ftnr'].unique()

    pair_count = min(len(unique_payment_ftnr), len(unique_invoice_ftnr))

    return pd.DataFrame({
        'inv_Subscriber Nr': group.name[0],
        'inv_Doc Type': group.name[1],
        'pmt_Ftnr': unique_payment_ftnr[:pair_count],
        'inv_Ftnr': unique_invoice_ftnr[:pair_count]
    })


# ---------------------------
# LOAD & PREPARE TAX DATA
# ---------------------------

raw_ft_data = pd.read_csv(
    r"S:\06.11.25\27259885_NEWCNEFINTRANSRPT.CSV",
    dtype=str, on_bad_lines='skip'
)

tax_raw = pd.read_excel(
    r"C:\Users\mturky\Documents\Tax 8.xlsx",
    dtype='str'
)

tax_data = tax_raw[TAX_COLUMNS].copy()
tax_data['Created Date'] = pd.to_datetime(tax_data['Created Date'])
tax_data = tax_data.loc[tax_data['Item Eng Name'] == 'Sub.beiN']
tax_data['Amount'] = pd.to_numeric(tax_data['Amount'])

tax_data.loc[
    tax_data['Payment Flag Id'].isin(['Normal payment', 'Automation']),
    'Payment Flag Id'
] = 'Payment'

print(f"Tax rows: {tax_data.shape[0]}")


# ---------------------------
# LOAD & PREPARE FT TRANS DATA
# ---------------------------

ft_data = raw_ft_data.copy()

ft_data = ft_data.loc[ft_data['Subscriber Type'].isin(VALID_SUBSCRIBER_TYPES)]
ft_data = ft_data.loc[ft_data['Doc Status'] == 'Posted']
ft_data = ft_data.loc[
    (ft_data['Payment Flag'].isin(VALID_PAYMENT_FLAGS)) |
    (ft_data['Payment Flag'].isna())
]

# remove subscribers with unwanted patterns
ft_data = ft_data.loc[
    (~ft_data['Subscriber Nr'].str.lower().str.contains('edd')) &
    (~ft_data['Subscriber Nr'].str.lower().str.contains('hu')) &
    (~ft_data['Subscriber Nr'].str.lower().str.contains('be'))
]

# convert types
ft_data['Amount'] = pd.to_numeric(ft_data['Amount'])
ft_data['Created Date'] = pd.to_datetime(
    ft_data['Created Date'],
    format='%d/%m/%Y %I:%M:%S %p'
)
ft_data['Period To'] = pd.to_datetime(ft_data['Period To'], format='%d/%m/%Y %I:%M:%S %p')
ft_data['Period From'] = pd.to_datetime(ft_data['Period From'], format='%d/%m/%Y %I:%M:%S %p')

# select only AUG data
ft_data = ft_data.loc[
    (ft_data['Created Date'] >= "2025-08-01") &
    (ft_data['Created Date'] <= "2025-08-31")
]

print(f"Filtered FT records: {ft_data.shape[0]}")

# ---------------------------
# SPLIT INTO INVOICES & PAYMENTS
# ---------------------------

invoice_data = ft_data.loc[ft_data['Doc Type'] == 'Invoice'].copy()
invoice_data = invoice_data.loc[invoice_data['Invoice Type'].isin(VALID_INVOICE_TYPES)]
invoice_data = invoice_data.loc[invoice_data['Amount'] > 0]
invoice_data = invoice_data.add_prefix("inv_")

print(f"Invoices: {invoice_data.shape[0]}")

payment_data = ft_data.loc[ft_data['Doc Type'].isin(['JV', 'Payment'])].copy()
payment_data = payment_data.loc[~payment_data['Jv Type'].isin(EXCLUDED_JV_TYPES)]
payment_data = payment_data.add_prefix("pmt_")

print(f"Payments: {payment_data.shape[0]}")


# ---------------------------
# FIRST MATCH: PAYMENT -> TAX USING FTNR
# ---------------------------

payments_with_tax = pd.merge(
    left=payment_data,
    right=tax_data[['Receiptno', 'Docinternalid']],
    left_on="pmt_Ftnr", right_on="Receiptno",
    how='left'
)

payments_unmatched = payments_with_tax[payments_with_tax['Receiptno'].isna()]
payments_matched = payments_with_tax[~payments_with_tax['Receiptno'].isna()]

print(f"Payments NOT found in tax: {payments_unmatched.shape[0]}")
print(f"Payments matched by FTNR: {payments_matched.shape[0]}")

# ---------------------------
# SECOND MATCH: MATCH USING SUBSCRIBER + DATE + AMOUNT
# ---------------------------

tax_unmatched = tax_data.loc[~tax_data['Receiptno'].isin(payment_data['pmt_Ftnr'])]

secondary_match = pd.merge(
    payments_unmatched,
    tax_unmatched,
    left_on=["pmt_Subscriber Nr", "pmt_Created Date", "pmt_Amount", "pmt_Doc Type"],
    right_on=["Subscriber Number", "Created Date", "Amount", "Payment Flag Id"],
    how='inner'
)

print(f"Secondary matches: {secondary_match.shape[0]}")

secondary_simple = secondary_match[['pmt_Subscriber Nr', 'pmt_Doc Type', 'pmt_Ftnr', 'Docinternalid_y']]

# ---------------------------
# UNIQUE PAIRING LOGIC
# ---------------------------

unique_payment_pairs = (
    secondary_simple.groupby(['pmt_Subscriber Nr', 'pmt_Doc Type'], group_keys=False)
    .apply(assign_unique_payment_pairs, include_groups=False)
    .reset_index(drop=True)
)

secondary_simple = secondary_simple.merge(unique_payment_pairs, how='inner')

secondary_match = secondary_match.merge(secondary_simple, how='inner')

# ---------------------------
# CONSOLIDATE ALL MATCHED PAYMENTS
# ---------------------------

all_linked_payments = pd.concat([payments_matched, secondary_match])

all_linked_payments['Docinternalid'] = all_linked_payments['Docinternalid'].fillna(
    all_linked_payments['Docinternalid_y']
)

final_payment_columns = [
    col for col in all_linked_payments.columns
    if not col.endswith('_y') and not col.startswith('Subscriber Number')
]

all_linked_payments = all_linked_payments[final_payment_columns]

print(f"All linked payments: {all_linked_payments.shape[0]}")

# ---------------------------
# INDICATE LOST PAYMENTS
# ---------------------------

lost_payments = payment_data.loc[~payment_data['pmt_Ftnr'].isin(all_linked_payments['pmt_Ftnr'])]

# Save output
all_linked_payments.to_csv("linked_payments.csv", index=False)

match_percentage = (all_linked_payments.shape[0] / payment_data.shape[0]) * 100
print(f"Linked {all_linked_payments.shape[0]} of {payment_data.shape[0]} payments ({match_percentage:.2f}%)")

