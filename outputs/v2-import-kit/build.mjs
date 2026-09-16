import fs from 'node:fs/promises';
import path from 'node:path';
import {Workbook, SpreadsheetFile} from '@oai/artifact-tool';
const out=path.dirname(new URL(import.meta.url).pathname.replace(/^\/([A-Za-z]:)/,'$1'));
const wb=Workbook.create();
const guide=wb.worksheets.add('Import guide');
const definitions=[];
function sheet(name,headers,rows){
  const s=wb.worksheets.add(name); definitions.push({name,headers,rows});
  const range=s.getRangeByIndexes(0,0,rows.length+1,headers.length); range.values=[headers,...rows];
  s.showGridLines=false; s.freezePanes.freezeRows(1);
  range.format.columnWidth=23; range.format.rowHeight=44; range.format.verticalAlignment='center'; range.format.wrapText=true;
  range.format.font.name='Arial'; range.format.font.size=11;
  const h=s.getRangeByIndexes(0,0,1,headers.length); h.format.fill='#172033'; h.format.font.color='#FFFFFF'; h.format.font.bold=true; h.format.wrapText=true; h.format.rowHeight=42;
  for(let c=0;c<headers.length;c++){
    const r=s.getRangeByIndexes(1,c,Math.max(1,rows.length),1);
    if(['amount','receipt','payment'].includes(headers[c])) r.setNumberFormat('#,##0.00');
    if(['account_number','iban','phone','ntn','strn','ftn'].includes(headers[c])) s.getRangeByIndexes(1,c,100,1).setNumberFormat('@');
    if(headers[c]==='date') { r.setNumberFormat('yyyy-mm-dd'); r.format.horizontalAlignment='center'; }
    if(['name','party','reference','remarks','description','address','beneficiary','client'].includes(headers[c])) s.getRangeByIndexes(0,c,rows.length+1,1).format.columnWidth=headers[c]==='remarks'?75:headers[c]==='description'?55:42;
    if(['direction','method','nature','reporting_class','active','kind','entity_type'].includes(headers[c])){
      const lists={direction:['receipt','payment'],method:['cash','transfer','cheque','card','other'],nature:['unclassified','operating','advance','loan','deposit','investment','capital','donation'],reporting_class:['unclassified','income','expense','other'],active:['true','false'],kind:name==='Accounts'?['cash','bank']:['customer','supplier','both','contractor','employee','other'],entity_type:['organization','person']};
      s.getRangeByIndexes(1,c,100,1).dataValidation={rule:{type:'list',values:lists[headers[c]]}};
    }
  }
  return s;
}
sheet('Categories',['code','name','description','active'],[
 ['TEST-INCOME','TEST Income','Synthetic income receipts','true'],['TEST-SUPPLIES','TEST Supplies','Synthetic supply payments','true'],['TEST-TRAVEL','TEST Travel','Synthetic travel costs','true'],['TEST-LOAN','TEST Loan principal','Principal movements, not income or expense','true'],['TEST-ADVANCE','TEST Advances','Advances awaiting settlement','true'],['TEST-DONATION','TEST Donations','Synthetic donation receipts','true'],
]);
sheet('Parties',['name','kind','entity_type','address','phone','email','ntn','strn','active'],[
 ['TEST Client organization','customer','organization','TEST Islamabad','','','','','true'],['TEST Contractor','contractor','person','','','','','','true'],['TEST Employee','employee','person','','','','','','true'],['TEST Sadat Poultry Service','supplier','organization','','','','','','true'],['TEST Mian Nisar Ahmed','supplier','person','','','','','','true'],['TEST Poultry Research Institute','customer','organization','','','','','','true'],
]);
sheet('Accounts',['name','kind','account_title','bank','branch','account_number','iban','active'],[
 ['TEST Bank','bank','','','','','','true'],['TEST Cash','cash','','','','','','true'],
]);
sheet('Projects',['code','name','reference','client','location','contact_name','email','active'],[
 ['TEST-CONTRACT','TEST General contract','TEST-CONTRACT-01','TEST Client organization','Islamabad','','','true'],['TEST-FEED','TEST Feed contract','TEST Framework 2025-26','TEST Poultry Research Institute','Rawalpindi','','','true'],
]);
const headers=['date','party','amount','direction','category','source','project','method','reference','handled_by','beneficiary','nature','reporting_class','counterparty','remarks'];
const tx=[
 ['2026-09-01','TEST Client organization',1500000,'receipt','TEST-INCOME','TEST Bank','TEST-CONTRACT','transfer','TEST-INC-01','TEST Finance','Muhammad Zakaria and Sons','operating','income','TEST Client organization','Synthetic income example'],
 ['2026-09-02','TEST Contractor',1000000,'payment','TEST-SUPPLIES','TEST Bank','TEST-CONTRACT','transfer','TEST-PAY-01','TEST Finance','TEST Contractor','operating','expense','TEST Contractor','Synthetic expense example inspired by payment register layout'],
 ['2026-09-03','TEST Contractor',220000,'payment','TEST-SUPPLIES','TEST Bank','TEST-CONTRACT','transfer','TEST-PAY-02','TEST Finance','TEST Contractor','operating','expense','TEST Contractor','Test editing allocations after importing this draft'],
 ['2026-09-04','TEST Contractor',200000,'payment','TEST-LOAN','TEST Bank','','transfer','TEST-LOAN-01','TEST Finance','TEST Contractor','loan','other','TEST Contractor','Loan principal issued; exclude from expense reports'],
 ['2026-09-05','TEST Contractor',600000,'receipt','TEST-LOAN','TEST Bank','','cheque','TEST-LOAN-02','TEST Finance','Muhammad Zakaria and Sons','loan','other','TEST Contractor','Loan principal returned; exclude from income reports'],
 ['2026-09-06','TEST Employee',100000,'payment','TEST-ADVANCE','TEST Cash','TEST-CONTRACT','cash','TEST-ADV-01','TEST Coordinator','TEST Employee','advance','other','TEST Employee','Temporary advance; expense recognition is not inferred'],
 ['2026-09-07','TEST Client organization',10000,'receipt','TEST-DONATION','TEST Bank','','transfer','TEST-DON-01','TEST Finance','Muhammad Zakaria and Sons','donation','income','TEST Client organization','Synthetic donation receipt example'],
 ['2026-09-08','TEST Employee',28000,'payment','TEST-TRAVEL','TEST Cash','TEST-CONTRACT','cash','TEST-EXP-01','TEST Coordinator','TEST Employee','operating','expense','TEST Employee','Synthetic travel expense example'],
].map(r=>[new Date(r[0]+'T00:00:00Z'),...r.slice(1)]);
sheet('Transactions',headers,tx);
const ledgerHeaders=['date','party','payment','receipt','category','source','project','method','reference','handled_by','beneficiary','nature','reporting_class','remarks'];
const ledger=[
 ['2025-09-25','TEST Sadat Poultry Service',130000,0,'TEST-SUPPLIES','TEST Bank','TEST-FEED','transfer','TEST-LED-01','TEST Finance','TEST Sadat Poultry Service','unclassified','unclassified','Screenshot excerpt: 20 bags; source account substituted for testing'],
 ['2025-09-25','TEST Sadat Poultry Service',320500,0,'TEST-SUPPLIES','TEST Bank','TEST-FEED','transfer','TEST-LED-02','TEST Finance','TEST Sadat Poultry Service','unclassified','unclassified','Screenshot excerpt: 50 bags; accounting classification left for review'],
 ['2025-09-30','TEST Mian Nisar Ahmed',71000,0,'TEST-SUPPLIES','TEST Bank','TEST-FEED','other','TEST-LED-03','TEST Finance','TEST Mian Nisar Ahmed','unclassified','unclassified','Screenshot excerpt: 10 bags; method not established, marked Other'],
 ['2026-01-22','TEST Poultry Research Institute',0,5009642,'TEST-INCOME','TEST Bank','TEST-FEED','other','TEST-LED-04','TEST Finance','Muhammad Zakaria and Sons','unclassified','unclassified','Screenshot receipt 1, included once; do not also import the repeated receipt schedule'],
].map(r=>[new Date(r[0]+'T00:00:00Z'),...r.slice(1)]);
sheet('Client ledger excerpt',ledgerHeaders,ledger);
const notes=[
 ['V2 testing and import workbook','Muhammad Zakaria and Sons, Islamabad'],
 ['Purpose','TEST data only. Replace example rows in a copy of this workbook for your own inputs.'],
 ['1. Import setup records','In Transaction register > Import setup records, import Categories, Parties, Accounts (type sources), then Projects.'],
 ['2. Transaction import','Choose Transactions in Import spreadsheet. Header row 1. Single amount mode. Map columns to matching field names. Date format ISO.'],
 ['Transactions: receipt control',2110000],['Transactions: payment control',1548000],
 ['3. Ledger import','Client ledger excerpt uses Separate receipt/payment columns. Map payment to Payment and receipt to Receipt. Header row 1; ISO dates.'],
 ['Ledger excerpt: receipt control',5009642],['Ledger excerpt: payment control',521500],
 ['4. Confirm only after review','Imports create drafts. Review classification, amounts, dates and supporting files, then submit to a separate reviewer.'],
 ['5. Additional fields','Beneficiary, handled_by, nature and reporting_class feed the new filters and grouped reports. Blank identifiers stay blank.'],
 ['6. Accounting classification','income requires receipt; expense requires payment; nature must be operating or donation. Principal and advances use other. Uncertain records stay unclassified.'],
 ['7. Remove testing records','Use Data management to remove/restore drafts and archive setup records. Confirmed transactions require reasoned cancellation by an authorized role.'],
 ['8. Avoid duplicate imports','Do not import a journal and its matching ledger copies as separate transactions. Repeated receipt schedules are excluded from this excerpt.'],
 ['Source of ledger excerpt','User-supplied ledger screenshot dated 8 September 2026. Four rows adapted; TEST prefixes and source account are substitutions. This is not the complete ledger.'],
 ['Source discrepancy for client review','Screenshot main totals: 70,438,638 payments and 59,202,802 receipts. Extra receipt schedule includes 4,409,259 not reflected in the displayed main total. Confirm original Excel before full migration.'],
 ['Extending a sheet','Append literal data rows under the existing headings. Keep control totals on this guide sheet, outside import data. Maximum 1,000 data rows per import.'],
 ['File attachments','Excel embedded images are not imported. Attach original supporting files to the resulting draft vouchers.'],
 ['Opening balances and transfers','Enter these in Openings / Transfers. Their import is not part of the receipt/payment spreadsheet format.'],
];
guide.getRangeByIndexes(0,0,notes.length,2).values=notes;
guide.showGridLines=false; guide.getRange('A1:B19').format.font.name='Arial'; guide.getRange('A1:B19').format.font.size=11;
guide.getRange('A1:A19').format.columnWidth=40; guide.getRange('B1:B19').format.columnWidth=110; guide.getRange('A1:B19').format.wrapText=true; guide.getRange('A1:B19').format.rowHeight=48;
guide.getRange('A1:B19').format.verticalAlignment='center';
guide.getRange('A1:B1').format.fill='#172033'; guide.getRange('A1:B1').format.font.color='#FFFFFF'; guide.getRange('A1:B1').format.font.bold=true;
for(const r of [5,6,8,9]) guide.getRange(`B${r}`).setNumberFormat('#,##0.00');
wb.recalculate();
console.log((await wb.inspect({kind:'table',range:'Transactions!A1:F4',include:'values',tableMaxRows:4,tableMaxCols:6})).ndjson);
console.log((await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#NUM!|#SPILL!',options:{useRegex:true,maxResults:10}})).ndjson);
await (await SpreadsheetFile.exportXlsx(wb)).save(path.join(out,'V2-Testing-and-Import.xlsx'));
for(const item of definitions){
 const rows=[item.headers,...item.rows].map(row=>row.map(v=>v instanceof Date?v.toISOString().slice(0,10):v));
 const csv=rows.map(row=>row.map(v=>'"'+String(v??'').replaceAll('"','""')+'"').join(',')).join('\r\n');
 await fs.writeFile(path.join(out,item.name.replaceAll(' ','-')+'.csv'),'\ufeff'+csv);
 const image=await wb.render({sheetName:item.name,range:`A1:${String.fromCharCode(64+Math.min(item.headers.length,6))}${Math.min(item.rows.length+1,5)}`,scale:1.4,format:'png'});
 await fs.writeFile(path.join(out,item.name.replaceAll(' ','-')+'.png'),new Uint8Array(await image.arrayBuffer()));
 if(item.headers.length>6) {
  const right=await wb.render({sheetName:item.name,range:`G1:${String.fromCharCode(64+item.headers.length)}${Math.min(item.rows.length+1,5)}`,scale:1,format:'png'});
  await fs.writeFile(path.join(out,item.name.replaceAll(' ','-')+'-fields.png'),new Uint8Array(await right.arrayBuffer()));
 }
}
const preview=await wb.render({sheetName:'Import guide',range:'A1:B9',scale:1,format:'png'});
await fs.writeFile(path.join(out,'Guide.png'),new Uint8Array(await preview.arrayBuffer()));
console.log('Workbook, CSV input sheets and previews exported.');
