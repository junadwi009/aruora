import React from "react";
export class ExperienceBoundary extends React.Component<{children:React.ReactNode},{failed:boolean}>{
 state={failed:false};static getDerivedStateFromError(){return {failed:true};}
 render(){return this.state.failed?<main className="aru-state-page"><h1>This screen could not be displayed.</h1><p>Refresh to recover. Unsaved work on this screen may be lost.</p><button className="aru-button" onClick={()=>window.location.reload()}>Reload application</button></main>:this.props.children;}
}
