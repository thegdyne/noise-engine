# P0 Blocking



## SC: getSynchronous Crash on Server Disconnect
`Server-getControlBusValue only supports local servers` error in `mod_osc.scd` and `mod_apply_v2.scd`.
- Wrap getSynchronous calls in try/catch, or use Bus.get with callback
