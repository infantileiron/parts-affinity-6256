/** @typedef {{id:number,code:string,equipment:string,parts:string[],note:string,station_code:?string,cycle:?string}} Job */
/** @typedef {{id:number,code:string,name:string}} Station */
/** @typedef {{id:number,station_code:string,cycle:string,equipment:string,state:'pending'|'active'|'void',version:number,valid_jobs:number,combo_counts:{parts:string[],count:number}[],checksum:string,supersedes_id:?number}} SummaryReport */
/** @typedef {{id:number,name:string,state:string,result:?object,source_manifest:?object,snapshot:?object}} MiningRun */
/** @typedef {{id:number,run_id:number,antecedent:string[],consequent:string[],support:number,confidence:number,lift:number}} AssociationRule */
/** @typedef {{id:number,name:string,rule_id:number,parts:string[],note:string,status:string}} Kit */
